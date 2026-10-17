import base64
import subprocess
import tempfile
import unittest
from pathlib import Path
from app.video import probe,frames

class VideoTests(unittest.TestCase):
    def test_real_jpeg_and_presentation_timestamps(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.mov'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=30',
                            '-t','2','-c:v','mpeg4',str(p)],check=True,timeout=15)
            self.assertAlmostEqual(probe(p)['duration'],2,places=1)
            sampled=frames(p,[0,.5,1,1.5])
            self.assertEqual(len(sampled),4)
            for f,target in zip(sampled,[0,.5,1,1.5]):
                self.assertLess(abs(f['timestamp_sec']-target),.04)
                self.assertTrue(base64.b64decode(f['image_base64']).startswith(b'\xff\xd8'))
    def test_invalid_mov(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'invalid.mov';p.write_text('not video')
            with self.assertRaises((ValueError,subprocess.CalledProcessError)):probe(p)

