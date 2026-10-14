# Potager-video

Vidéo motion design verticale (TikTok / YouTube Shorts) : **planter l'ail et l'échalote — automne ou printemps ?**

- Rendu final : `output/ail_echalote_printemps_1080x1920.mp4` (1080×1920, 30 i/s, 71,6 s, AAC 48 kHz, −14 LUFS)
- Voix off : `assets/audio/voix.mp3` (+ horodatage mot à mot `voix_mots.json`)
- Photos réelles détourées (Open Images, Google — CC BY 2.0) : `assets/images/`
- Polices : Poppins, Lilita One (SIL OFL)

## Re-générer

```bash
pip install pillow numpy scipy soundfile
python3 src/render.py                      # vidéo complète -> output/
python3 src/render.py --preview 3.2,20.9   # images de contrôle
```

- `src/scenes.py` : storyboard (14 scènes, temps calés sur la voix) + effets sonores associés
- `src/gfx.py` : décor beige, table / terre, textes, icônes, badges, calendriers
- `src/sfx.py` : effets sonores synthétisés (whoosh, pop, ding, oiseaux, pluie, clic…)
- `src/render.py` : sous-titres mot à mot, transitions « whip », mixage et encodage
