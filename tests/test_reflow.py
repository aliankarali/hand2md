import unittest

from hand2md.reflow import reflow


class ReflowTest(unittest.TestCase):
    def test_joins_lines_within_a_paragraph(self):
        self.assertEqual(
            reflow("Ich komme gerne und bringe\neinen Kuchen mit.\n\nBis bald"),
            "Ich komme gerne und bringe einen Kuchen mit.\n\nBis bald",
        )

    def test_undoes_line_break_hyphenation(self):
        self.assertEqual(reflow("zum Som-\nmerfest"), "zum Sommerfest")

    def test_keeps_compound_hyphen_before_capital(self):
        self.assertEqual(reflow("per E-\nMail"), "per E-Mail")

    def test_keeps_suspended_hyphen(self):
        self.assertEqual(reflow("Kunden-\nund Vertragsdaten"), "Kunden- und Vertragsdaten")

    def test_does_not_treat_spaced_dash_as_hyphenation(self):
        self.assertEqual(reflow("Treffen -\nmorgen"), "Treffen - morgen")

    def test_list_items_stay_separate_and_absorb_continuations(self):
        self.assertEqual(
            reflow("- Milch\n- Brot vom Bäcker\nund Kuchen\n1. eins\n2. zwei"),
            "- Milch\n- Brot vom Bäcker und Kuchen\n1. eins\n2. zwei",
        )

    def test_heading_is_never_merged(self):
        self.assertEqual(reflow("# Notizen\nerste Zeile\nzweite Zeile"), "# Notizen\nerste Zeile zweite Zeile")

    def test_table_rows_and_comments_stay(self):
        text = "<!-- note -->\n\n| a | b |\n|---|---|\n| 1 | 2 |"
        self.assertEqual(reflow(text), text)

    def test_checkboxes_are_list_items(self):
        self.assertEqual(reflow("- [ ] eins\n- [x] zwei"), "- [ ] eins\n- [x] zwei")

    def test_strips_indentation_and_collapses_blank_lines(self):
        self.assertEqual(reflow("    eingerückt\nweiter\n\n\n\nneu"), "eingerückt weiter\n\nneu")

    def test_code_fences_untouched(self):
        text = "```\na\nb\n```"
        self.assertEqual(reflow(text), text)


if __name__ == "__main__":
    unittest.main()
