import unittest

from app.parsers import parse_workout


class WorkoutDurationTests(unittest.TestCase):
    def test_command_keeps_duration_and_description(self):
        workout = parse_workout('/log_workout 30 min bike')
        self.assertEqual(workout.duration_minutes, 30)
        self.assertEqual(workout.workout_type, 'bike')
        self.assertEqual(workout.summary, '30 min bike')
        self.assertEqual(workout.source, 'manual_command')

    def test_natural_text_and_minute_units(self):
        for unit in ('min', 'mins', 'minute', 'minutes'):
            with self.subTest(unit=unit):
                workout = parse_workout(f'did 30 {unit} bike')
                self.assertEqual(workout.duration_minutes, 30)
                self.assertEqual(workout.source, 'natural_text')

    def test_supported_range_boundaries(self):
        for duration in (1, 600):
            with self.subTest(duration=duration):
                self.assertEqual(
                    parse_workout(f'{duration} min walk').duration_minutes,
                    duration,
                )

    def test_out_of_range_durations_are_rejected(self):
        for duration in (0, -5, 601):
            with self.subTest(duration=duration):
                with self.assertRaises(ValueError):
                    parse_workout(f'{duration} min walk')

    def test_fractional_tokens_are_not_parsed_as_integer_suffixes(self):
        for duration in ('30.5', '30,5', '-0.5', '-0,5', '30.125', '.5'):
            for prefix in ('/log_workout ', 'did '):
                with self.subTest(duration=duration, prefix=prefix):
                    with self.assertRaises(ValueError):
                        parse_workout(f'{prefix}{duration} min bike')

    def test_default_workout_description_is_preserved(self):
        workout = parse_workout('30 min')
        self.assertEqual(workout.workout_type, 'workout')
        self.assertEqual(workout.summary, '30 min workout')


if __name__ == '__main__':
    unittest.main()
