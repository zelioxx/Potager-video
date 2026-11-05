# Potager-video

Vidéos courtes verticales (TikTok / Reels / Shorts) d'astuces potager et plantes, en français.

## Base de références

Tout ce qui sert d'inspiration est rangé dans [`references/`](references/) :

| Dossier / fichier | Contenu |
|---|---|
| [`references/STYLE.md`](references/STYLE.md) | **Bible de style** : structure narrative, ton, direction artistique, typo, couleurs, rythme, son |
| [`references/scripts.md`](references/scripts.md) | Scripts complets des vidéos de référence, avec timecodes et incrustations |
| `references/videos/` | Les vidéos de référence originales |
| `references/planches/` | Planches contact (1 image toutes les 2 s) |
| `references/frames/` | Images clés (1 toutes les 5 s, résolution d'origine) |
| `references/ocr/` | Sous-titres bruts extraits par OCR (JSON) |

### Vidéos de référence

| # | Sujet | Accroche | Durée |
|---|---|---|---|
| 01 | Faire repousser du gingembre | DES YEUX ? | 70 s |
| 02 | Bouturer une feuille de succulente | UNE FEUILLE TOMBE | 70 s |
| 03 | Récolter les graines d'œillet d'Inde | ŒILLET FANÉ ? | 68 s |
| 04 | Faire fleurir un cactus de Noël le 24 décembre | NOËL EN MARS ? | 70 s |

## Vidéos produites

| # | Sujet | Fichier |
|---|---|---|
| 01 | L'eau de cuisson des pâtes pour les plantes (21 s) | [`projets/01-eau-de-cuisson-pates/`](projets/01-eau-de-cuisson-pates/) |

## Générer une nouvelle vidéo

À fournir : le **sujet**, le **son** (voix off), et si possible les **images**.

Chaque vidéo est une page HTML animée (`projets/<nom>/index.html`) qui utilise la charte commune
(`tools/potager.css`, `tools/potager.js` : fond beige, gros titres, sous-titres avec mot-clé jaune),
rendue image par image puis assemblée avec la voix :

```bash
node tools/render.js projets/<nom>/index.html projets/<nom>/voix.mp3 projets/<nom>/video.mp4
```

Prérequis : Node.js + Playwright (Chromium), ffmpeg.
