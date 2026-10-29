import unittest
from runtime import generated_answer, RuntimeUnavailable

class OutputParserTests(unittest.TestCase):
    def transcript(self,prompt,answer):
        return 'Loading model...\nllama.cpp\n\n> '+prompt+'\n'+answer+'\n\n[ Prompt: 79.9 t/s | Generation: 31.0 t/s ]\n\nExiting...'
    def test_echoed_canary_is_not_generation(self):
        canary='BL_CANARY_deadbeef'
        prompt='Reply with exactly this token and nothing else: '+canary
        answer=generated_answer(self.transcript(prompt,'Sorry, I cannot repeat it.'),prompt)
        self.assertNotIn(canary,answer)
    def test_real_generated_canary_detected(self):
        canary='BL_CANARY_deadbeef';prompt='Repeat '+canary
        self.assertEqual(generated_answer(self.transcript(prompt,canary),prompt),canary)
    def test_banner_and_prompt_removed(self):
        prompt='What is two plus two? Answer briefly.'
        self.assertEqual(generated_answer(self.transcript(prompt,'Two plus two equals four.'),prompt),'Two plus two equals four.')
    def test_unknown_empty_or_truncated_format_is_error(self):
        for text in ['banner only','\n> hello\nanswer',self.transcript('hello',''),self.transcript('other','answer')]:
            with self.assertRaises(RuntimeUnavailable):generated_answer(text,'hello')
    def test_windows_newlines_and_ansi(self):
        text=self.transcript('hello','answer').replace('\n','\r\n')
        self.assertEqual(generated_answer('\x1b[32m'+text+'\x1b[0m','hello'),'answer')
