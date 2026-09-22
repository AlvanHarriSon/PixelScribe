import base64
import io
import logging
from pathlib import Path
import queue
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import FileDescriptor as module
from PIL import Image


def descriptor():
    app = module.FileDescriptor.__new__(module.FileDescriptor)
    app.queue = queue.Queue()
    app.cancel_event = threading.Event()
    app.logger = logging.getLogger('test')
    app.logger.addHandler(logging.NullHandler())
    app.logger.propagate = False
    app.supported_image_types = ['.png', '.jpg', '.bmp', '.gif']
    app.supported_pdf_types = ['.pdf']
    app.client = Mock()
    app.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='description'))])
    app.is_processing = False
    app.worker_thread = None
    app.status_var = Mock()
    return app


class DescriptorTests(unittest.TestCase):
    def test_payload_is_png(self):
        app = descriptor()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.bmp'
            with Image.new('RGB', (3, 3), 'red') as image:
                image.save(path)
            payload = base64.b64decode(app.encode_image(path))
            with Image.open(io.BytesIO(payload)) as image:
                self.assertEqual(image.format, 'PNG')
                self.assertEqual(image.size, (3, 3))

    def test_pdf_limit_snapshot_and_cleanup(self):
        app = descriptor()
        app.max_pages_var = Mock()
        app.max_pages_var.get.side_effect = AssertionError('worker accessed Tk')
        with patch.object(module, 'convert_from_path', return_value=[Image.new('RGB', (1, 1))]) as convert:
            paths = app.pdf_to_images('test.pdf', 2)
        self.assertEqual(convert.call_args.kwargs['last_page'], 2)
        for path in paths:
            self.assertTrue(Path(path).exists())
            Path(path).unlink()

    def test_partial_pdf_conversion_cleans_files(self):
        app = descriptor()
        page = Mock()
        page.save.side_effect = OSError('disk full')
        with tempfile.TemporaryDirectory() as directory:
            factory = module.tempfile.NamedTemporaryFile
            with patch.object(module, 'convert_from_path', return_value=[page]), patch.object(module.tempfile, 'NamedTemporaryFile', side_effect=lambda **kw: factory(dir=directory, **kw)):
                with self.assertRaises(OSError):
                    app.pdf_to_images('bad.pdf', 2)
            self.assertEqual(list(Path(directory).iterdir()), [])
        page.close.assert_called_once()

    def test_duplicate_start_does_not_touch_inputs(self):
        app = descriptor()
        app.is_processing = True
        app.generate_description()
        app.status_var.set.assert_called_once()

    def test_worker_never_uses_tk_on_failure(self):
        app = descriptor()
        app.encode_image = Mock(side_effect=OSError('broken image'))
        with patch.object(module.messagebox, 'askyesno', side_effect=AssertionError('Tk from worker')) as dialog:
            worker = threading.Thread(target=app._worker, args=(['a.png'], 'describe', 'model', 2))
            worker.start()
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
        dialog.assert_not_called()
        app.status_var.set.assert_not_called()
        messages = list(app.queue.queue)
        self.assertTrue(any(kind == 'error' for kind, _ in messages))
        self.assertEqual(messages[-1], ('done', None))
        self.assertIn('失败', messages[-2][1])

    def test_cancelled_worker_is_not_reported_complete(self):
        app = descriptor()
        app.cancel_event.set()
        app._worker(['a.png'], 'describe', 'model', 2)
        self.assertIn(('status', '任务已取消'), list(app.queue.queue))
        app.client.chat.completions.create.assert_not_called()

    def test_cancel_during_request_discards_result(self):
        app = descriptor()
        app.encode_image = Mock(return_value='png')
        def response(**kwargs):
            app.cancel_event.set()
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='late'))])
        app.client.chat.completions.create.side_effect = response
        self.assertIsNone(app._describe_image('a.png', 'prompt', 'model'))

    def test_retry_limit_and_mime(self):
        app = descriptor()
        app.encode_image = Mock(return_value='encoded')
        exc = RuntimeError('limited')
        exc.status_code = 429
        app.client.chat.completions.create.side_effect = exc
        with patch.object(app.cancel_event, 'wait', return_value=False), self.assertRaises(RuntimeError):
            app._describe_image('a.png', 'prompt', 'model')
        self.assertEqual(app.client.chat.completions.create.call_count, 4)
        request = app.client.chat.completions.create.call_args.kwargs
        self.assertEqual(request['messages'][1]['content'][0]['image_url']['url'], 'data:image/png;base64,encoded')

    def test_pdf_worker_removes_temporary_files_on_cancel(self):
        app = descriptor()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'page.png'
            path.write_bytes(b'page')
            app.pdf_to_images = Mock(return_value=[str(path)])
            app._describe_image = Mock(side_effect=lambda *args: app.cancel_event.set())
            app._worker(['a.pdf'], 'describe', 'model', 2)
            self.assertFalse(path.exists())

    def test_empty_model_response_is_failure(self):
        app = descriptor()
        app.encode_image = Mock(return_value='png')
        app.client.chat.completions.create.return_value.choices[0].message.content = None
        with self.assertRaises(ValueError):
            app._describe_image('a.png', 'prompt', 'model')

    def test_history_sort_tolerates_invalid_timestamp(self):
        app = descriptor()
        tree = Mock()
        tree.get_children.return_value = ['recent', 'invalid', 'old']
        tree.set.side_effect = lambda key, col: {
            'recent': '2026-09-22T12:00:00', 'invalid': '', 'old': '2020-01-01T00:00:00'}[key]
        app.treeview_sort_column(tree, 'ts', False)
        self.assertEqual([call.args[0] for call in tree.move.call_args_list], ['invalid', 'old', 'recent'])


if __name__ == '__main__':
    unittest.main()
