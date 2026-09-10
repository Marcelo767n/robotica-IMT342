import unittest

import numpy as np

from irb120_hito1.motion import DEMO_KEYFRAMES, interpolate_demo


class TestMotionDemo(unittest.TestCase):
    def test_reaches_keyframes_at_segment_boundaries(self) -> None:
        duration = 3.0
        for index, expected in enumerate(DEMO_KEYFRAMES[:-1]):
            np.testing.assert_allclose(
                interpolate_demo(index * duration, duration),
                expected,
                atol=1.0e-12,
            )

    def test_interpolation_stays_between_neighboring_keyframes(self) -> None:
        duration = 3.0
        for index in range(len(DEMO_KEYFRAMES) - 1):
            midpoint = interpolate_demo((index + 0.5) * duration, duration)
            lower = np.minimum(DEMO_KEYFRAMES[index], DEMO_KEYFRAMES[index + 1])
            upper = np.maximum(DEMO_KEYFRAMES[index], DEMO_KEYFRAMES[index + 1])
            self.assertTrue(np.all(midpoint >= lower))
            self.assertTrue(np.all(midpoint <= upper))


if __name__ == "__main__":
    unittest.main()
