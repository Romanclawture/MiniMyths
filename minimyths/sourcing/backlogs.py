"""Curated story backlogs per genre.

The Greek myths list is seeded from crowd-pleasers covered by the Greeking Out
podcast — proven kid/family-friendly bangers with strong characters and clear
three-act shapes. Order is a rough priority: lead with the most recognizable
names to help early channel discovery.
"""

BACKLOGS = {
    "greek_myths": [
        {"title": "Hercules and the Twelve Labors", "wikipedia": "Labours_of_Hercules",
         "hook": "The gods gave him impossible chores. He made them look easy."},
        {"title": "Perseus and Medusa", "wikipedia": "Perseus",
         "hook": "How do you fight a monster you can't even look at?"},
        {"title": "Theseus and the Minotaur", "wikipedia": "Theseus",
         "hook": "A maze, a monster, and a ball of string that saved a kingdom."},
        {"title": "The Trojan Horse", "wikipedia": "Trojan_Horse",
         "hook": "The greatest military trick in history was a wooden gift."},
        {"title": "Odysseus and the Cyclops", "wikipedia": "Polyphemus",
         "hook": "Trapped in a cave with a giant who eats men. His weapon? A fake name."},
        {"title": "Pandora's Box", "wikipedia": "Pandora",
         "hook": "One box. One rule. You already know how this ends."},
        {"title": "Icarus and Daedalus", "wikipedia": "Icarus",
         "hook": "His father built him wings and gave him one warning."},
        {"title": "King Midas and the Golden Touch", "wikipedia": "Midas",
         "hook": "He wished everything he touched turned to gold. Everything did."},
        {"title": "Persephone and Hades", "wikipedia": "Persephone",
         "hook": "Why we have winter, according to the Greeks."},
        {"title": "Arachne the Weaver", "wikipedia": "Arachne",
         "hook": "She said she was better than a goddess. She was right. It cost her."},
        {"title": "Prometheus Steals Fire", "wikipedia": "Prometheus",
         "hook": "He stole from the gods to save humanity. The punishment was forever."},
        {"title": "Orpheus and Eurydice", "wikipedia": "Orpheus",
         "hook": "He walked into the underworld with nothing but a lyre. One rule: don't look back."},
        {"title": "Atalanta the Huntress", "wikipedia": "Atalanta",
         "hook": "She could outrun any man alive — so she made it the price of her hand."},
        {"title": "Bellerophon and Pegasus", "wikipedia": "Bellerophon",
         "hook": "He tamed a flying horse and slew the Chimera. Then he flew too high."},
        {"title": "Jason and the Golden Fleece", "wikipedia": "Jason",
         "hook": "A crew of heroes, a dragon that never sleeps, and a witch who changes everything."},
    ],
}


def get_backlog(genre: str) -> list[dict]:
    if genre not in BACKLOGS:
        raise KeyError(f"No backlog for genre '{genre}'. Available: {', '.join(BACKLOGS)}")
    return BACKLOGS[genre]
