# 01 — L'eau de cuisson des pâtes

## v2 — vraies photos + éléments 3D (`eau-de-cuisson-pates-photos-3d.mp4`)

Page : `photos.html` · bruitages : `bruitages_photos.json`

| t (s) | Photos | 3D / effets |
|---|---|---|
| 0.0 | Casserole en ébullition sur le plan de travail (fond cuisine) | Vapeur 3D, titre 3D « L'EAU DES PÂTES ? » |
| 1.55 | Casserole qui verse sur le pothos | Filet d'eau en gouttes 3D |
| 2.9 | Pothos sain → pothos sec | **Nuit** + **pluie 3D** + éclair (tonnerre) |
| 4.05 | Casserole + loupe (grossissement réel) | Cristaux de sel 3D dans la loupe, « 1 DÉTAIL » |
| 6.15 | Boîte de sel qui verse dans la casserole | Grains de sel 3D, « LE SEL » |
| 7.3 | Pot en coupe : racines saines → pourries (zoom) | Cristaux de sel 3D qui s'accumulent dans la terre |
| 11.1 | Boîte de sel | Panneau « interdit » 3D, « SANS SEL » |
| 11.95 | Casserole à la fenêtre (fond fenêtre) | La vapeur 3D s'éteint, compteur 3D 95 → 20 °C, teinte froide |
| 12.85 | Arrosoir zinc + pothos sain | Gouttes 3D, badge calendrier |
| 14.15 | Casserole + légumes (oignon, tomate, citrouille, concombre) qui tombent | Vapeur, éclaboussures 3D, « LE MEILLEUR » |
| 16.7 | Idem | Bulles 3D K / Ca / Mg, « MINÉRAUX » |
| 18.05 | Logo Les Potagers de Louis | Logo en carte 3D qui pivote, bouton S'ABONNER |

Sous-titres : texte 3D (blanc, mot-clé jaune, tranche verte), calés sur la voix.

```bash
python3 tools/sfx.py projets/01-eau-de-cuisson-pates/bruitages_photos.json
node tools/render.js projets/01-eau-de-cuisson-pates/photos.html projets/01-eau-de-cuisson-pates/mix_photos.wav projets/01-eau-de-cuisson-pates/eau-de-cuisson-pates-photos-3d.mp4
```

---

## v1 — illustrations (`eau-de-cuisson-pates.mp4`)

- **Vidéo finale** : `eau-de-cuisson-pates.mp4` (1080×1920, 30 i/s, 21,1 s, voix normalisée à -14 LUFS)
- **Voix off** : `voix.mp3` (fournie)
- **Bruitages** : `bruitages.json` (sons synthétisés par `tools/sfx.py`, mixés sous la voix)
- **Animation** : `index.html` (illustrations SVG dessinées, charte de `references/STYLE.md`)

## Texte (transcrit de la voix off)

> L'eau de cuisson de tes pâtes peut nourrir tes plantes… ou les tuer. Tout dépend d'un seul détail. Le sel.
> L'eau salée assèche les racines et le sel s'accumule dans la terre. Sans sel et bien refroidie ? Oui, de temps en temps.
> Mais le meilleur, c'est l'eau de cuisson des légumes. Elle est pleine de minéraux.
> Et pour plus d'astuces, abonnez-vous au Potager de Louis.

## Découpage

| t (s) | Plan | Gros titre |
|---|---|---|
| 0.0 | Casserole de pâtes qui fume | L'EAU DES PÂTES ? |
| 1.55 | La casserole verse l'eau sur une plante | |
| 2.9 | La plante fane | |
| 4.05 | Loupe sur l'eau : cristaux de sel | 1 DÉTAIL |
| 6.15 | Salière qui verse dans la casserole | LE SEL |
| 7.3 | Pot en coupe : racines qui sèchent, sel qui s'accumule | |
| 11.1 | Salière barrée | SANS SEL |
| 11.95 | Thermomètre 95 → 20 °C (fond gris-bleu) | |
| 12.85 | Arrosoir sur plante + badge calendrier | |
| 14.15 | Casserole de légumes, légumes qui tombent | LE MEILLEUR |
| 16.7 | Bulles K / Ca / Mg | MINÉRAUX |
| 18.05 | Plante en forme + bouton S'ABONNER | LE POTAGER DE LOUIS |

## Bruitages

| t (s) | Son |
|---|---|
| 0.0 | pop (titre) + casserole qui frémit |
| 1.5 / 4.0 / 7.3 / 11.9 / 14.1 / 18.0 | whoosh aux changements de plan |
| 1.95 | eau versée sur la plante |
| 2.9 | sifflet descendant (la plante fane) |
| 4.6 | scintillement (loupe) |
| 6.4 | salière secouée + grains |
| 7.6 → 10.9 | craquements (racines sèches) puis cristaux de sel |
| 11.3 | buzzer « interdit » |
| 12.05 | tics descendants (thermomètre) |
| 12.85 → 13.7 | pages de calendrier + arrosoir |
| 15.2 → 15.9 | plops des légumes dans l'eau |
| 16.75 → 17.25 | bulles K / Ca / Mg |
| 20.0 / 20.1 | clic du bouton + ding « abonné » |

## Re-générer

```bash
python3 tools/sfx.py projets/01-eau-de-cuisson-pates/bruitages.json
node tools/render.js projets/01-eau-de-cuisson-pates/index.html projets/01-eau-de-cuisson-pates/mix.wav projets/01-eau-de-cuisson-pates/eau-de-cuisson-pates.mp4
```
