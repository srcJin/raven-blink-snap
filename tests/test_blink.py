import unittest
from blink import BlinkDetector


class DetectorTests(unittest.TestCase):
    def run_trace(self, losses, duration=5, stalled=None):
        d = BlinkDetector()
        shots = []
        for i in range(int(duration/0.01)):
            t=round(i*0.01, 2)
            if stalled and stalled[0] <= t < stalled[1]:
                continue
            tracked=not any(start <= t < end for start,end in losses)
            if d.sample(tracked,t):
                shots.append(t)
        return shots

    def test_two_short_losses_capture_once(self):
        self.assertEqual(self.run_trace([(0.5,0.63),(0.9,1.03)]),[1.03])

    def test_one_blink_does_not_capture(self):
        self.assertEqual(self.run_trace([(0.5,0.63)]),[])

    def test_long_loss_resets_sequence(self):
        self.assertEqual(self.run_trace([(0.5,0.63),(0.9,2),(2.3,2.43)]),[])

    def test_noise_is_not_a_blink(self):
        self.assertEqual(self.run_trace([(0.5,0.52),(0.8,0.82)]),[])

    def test_separated_blinks_do_not_capture(self):
        self.assertEqual(self.run_trace([(0.5,0.63),(1.5,1.63)]),[])

    def test_cooldown_and_rearming(self):
        self.assertEqual(self.run_trace([(0.5,0.63),(0.9,1.03),(1.4,1.53),(1.8,1.93),(3.5,3.63),(3.9,4.03)]),[1.03,4.03])

    def test_initial_tracking_loss_is_ignored(self):
        self.assertEqual(self.run_trace([(0,0.13),(0.4,0.53)]),[])

    def test_insufficient_recovery_resets(self):
        self.assertEqual(self.run_trace([(0.5,0.63),(0.65,0.78)]),[])

    def test_poll_stall_is_not_a_blink(self):
        self.assertEqual(self.run_trace([(0.5,0.63),(0.9,1.03)],stalled=(0.54,0.94)),[])

if __name__ == '__main__':
    unittest.main()
