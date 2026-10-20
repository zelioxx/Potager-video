# Potager-video

Vidéos motion design verticales (TikTok / YouTube Shorts), même direction artistique (fond beige, photos réelles détourées) :

1. **Ail & échalote : automne ou printemps ?** — `output/ail_echalote_printemps_1080x1920.mp4`
2. **Refaire pousser un poireau à partir du pied** — `output/poireau_repousse_1080x1920.mp4` (60,7 s ; voix `assets/audio/poireau/`, photos `assets/images/poireau/`)
3. **N'arrose pas trop tes plantes d'intérieur** — `output/arrosage_plantes_1080x1920.mp4` (76,8 s ; voix `assets/audio/arrosage/`, photos `assets/images/arrosage/`)
4. **Bouturer les petits fruitiers** — `output/bouture_petits_fruitiers_1080x1920.mp4` (39,9 s ; voix `assets/audio/bouture/`, photos `assets/images/bouture/`)
5. **Bouturer les aromatiques** — `output/bouture_aromatiques_1080x1920.mp4` (41,4 s ; intro = vidéo fournie `assets/video/intro_thym.mp4`, voix `assets/audio/aromatiques/`)
6. **Compost : les 3 erreurs** — `output/compost_3_erreurs_1080x1920.mp4` (37,8 s ; intro = vidéo fournie `assets/video/intro_compost.mp4`, voix `assets/audio/compost/`)
7. **Refaire pousser un ananas** — `output/ananas_bouture_1080x1920.mp4` (68,4 s ; voix `assets/audio/ananas/` ; déposer `assets/video/intro_ananas.mp4` pour l'intro vidéo)

## Vidéo ail & échalote

- Rendu final : `output/ail_echalote_printemps_1080x1920.mp4` (1080×1920, 30 i/s, 71,6 s, AAC 48 kHz, −14 LUFS)
- Voix off : `assets/audio/voix.mp3` (+ horodatage mot à mot `voix_mots.json`)
- Photos réelles détourées (Open Images, Google — CC BY 2.0) : `assets/images/`
- Polices : Poppins, Lilita One (SIL OFL)

## Re-générer

```bash
pip install pillow numpy scipy soundfile
python3 src/render.py ail                      # vidéo ail & échalote -> output/
python3 src/render.py poireau                  # vidéo poireau -> output/
python3 src/render.py arrosage                 # vidéo arrosage -> output/
python3 src/render.py bouture                  # vidéo bouturage -> output/
python3 src/render.py aromatiques              # vidéo aromatiques -> output/
python3 src/render.py compost                  # vidéo compost -> output/
python3 src/render.py ananas                   # vidéo ananas -> output/
python3 src/render.py poireau --preview 3,20   # images de contrôle
```

- `src/scenes.py` / `src/scenes_poireau.py` : storyboards (temps calés sur la voix) + effets sonores associés
- `src/gfx.py` : décor beige, table / terre, textes, icônes, badges, calendriers
- `src/sfx.py` : effets sonores synthétisés (whoosh, pop, ding, oiseaux, pluie, clic…)
- `src/render.py` : sous-titres mot à mot, transitions « whip », mixage et encodage
