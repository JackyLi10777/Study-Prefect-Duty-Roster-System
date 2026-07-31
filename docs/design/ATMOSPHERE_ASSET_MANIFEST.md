# Atmosphere Asset Manifest

This manifest is the integrity and placement source for generated atmosphere artwork. The English prompts are authoritative; the Chinese notes describe the intended review outcome. No project database, roster, screenshot, log, credential, school identity, or user content is used as model input.

## Global generation and use contract

- Tool: OpenAI built-in image generation, followed only by local Pillow colour/size/WebP normalisation.
- Light master: original 16:9 generation. Dark companion: image edit of the accepted light master, changing only light, colour temperature, and evening atmosphere while preserving geometry, object placement, negative space, and crop.
- Delivery: `1600×900` WebP, target `≤180 KB`, hard limit `≤250 KB`, no metadata required by the application.
- Mandatory exclusions: people, students, hands, faces, names, readable text or numbers, school crest, logo, trademark, watermark, fake UI, screens, devices showing content, and identifiable campus scenes.
- Allowed placements: route header, narrative hero, empty state, or non-sensitive reading surface.
- Forbidden placements: tables, forms, student names, fairness values, warnings, interactive controls, confirmation dialogs, Viewer, downloads, and PDFs.
- Images carry no required information. A solid/gradient veil owns text contrast; a missing image leaves a complete usable interface.

## Source prompts

### `weekly-operations`

Light master prompt:

> Create an original 16:9 atmospheric editorial still life for a premium bilingual school duty-operations web application. Show an orderly weekly planning desk on the right: a blank unlabelled planning sheet suggested only by subtle grid lines, a graphite pencil, layered warm paper, one restrained woven service thread, and a small neutral paper marker. Keep the left 55% quiet, pale, low-detail negative space for a heading. Soft morning daylight, mineral white, warm parchment, muted slate blue and restrained teal; realistic materials with gentle editorial stylisation, calm, dignified, precise, static, no fake product mockup. No people, students, hands, faces, names, readable text, letters, numbers, school crest, logo, trademark, watermark, UI screenshot, screen, device content, identifiable school or dramatic lens flare.

Review intent／審核意圖：值班流程可辨識，但沒有真實校務資料；左側標題安全區完整。

### `people-fairness`

Light master prompt:

> Create an original 16:9 atmospheric editorial still life for a premium bilingual school duty-operations web application. On the right, arrange several perfectly blank index cards and small abstract geometric markers in a balanced, equitable rhythm, connected by one restrained woven thread with equal visual weight. Keep the left 55% quiet, pale, low-detail negative space for a heading. Soft morning daylight, warm paper, linen, muted slate blue, desaturated teal and a tiny restrained gold accent; realistic materials with gentle editorial stylisation, calm, humane, fair, static. Do not show people, portraits, silhouettes, hands, names, readable text, letters, numbers, wallets, money, legal scales, gavels, school crest, logo, trademark, watermark, UI screenshot, screen, device content or identifiable school.

Review intent／審核意圖：以抽象秩序表達公平，不把學生、法律或金錢意象帶入頁面。

### `administration-recovery`

Light master prompt:

> Create an original 16:9 atmospheric editorial still life for a premium bilingual school duty-operations web application. On the right, compose a precise brass-and-slate gear, a closed archival box, a simple physical key and a neatly returned woven thread on a trustworthy recovery workbench. Keep the left 55% quiet, pale, low-detail negative space for a heading. Soft controlled morning light, porcelain, pale timber, muted slate blue and restrained brass; realistic materials with gentle editorial stylisation, secure, recoverable, calm, static. No fake interface, password field, login screen, monitor, device content, people, students, hands, faces, names, readable text, letters, numbers, school crest, logo, trademark, watermark or identifiable school.

Review intent／審核意圖：齒輪、封存與復原語意清楚，但不暗示平台保存密碼。

### `support-lifeline`

Light master prompt:

> Create an original 16:9 atmospheric editorial still life for a premium bilingual school duty-operations web application. On the right, show a closed report folder with completely blank surfaces, a sealed unaddressed envelope, one carefully repaired woven thread and a soft task lamp casting a reassuring pool of light. Keep the left 55% quiet, pale, low-detail negative space for a heading. Warm mineral white, parchment, muted slate blue and restrained teal; realistic materials with gentle editorial stylisation, responsive, reassuring, calm, static. No readable writing, labels, stamps, addresses, people, students, hands, faces, names, letters, numbers, school crest, logo, trademark, watermark, UI screenshot, screen, device content or identifiable school.

Review intent／審核意圖：支援與修復感清楚，沒有可讀事故內容或個人資料。

### `devotional` v2

Light master prompt:

> Create an original 16:9 sacred editorial still life for a dignified bilingual Daily Verse reading surface. Preserve a large uninterrupted parchment-toned reading-safe area across the left 58%. On the right, place an open book with completely blank softly textured pages beside a quiet window, a restrained woven light thread and gentle morning illumination; the book must not contain readable marks. Warm dawn parchment, ivory, muted blue-grey and restrained antique gold; contemplative, reverent, serene, premium, realistic materials with gentle editorial stylisation, static. No people, students, hands, faces, names, readable text, letters, numbers, cross-shaped branding, school crest, logo, trademark, watermark, UI screenshot, screen, device content or identifiable school.

Review intent／審核意圖：同一窗邊與書本構圖支援明暗配對；左側為完整經文閱讀面。

## Dark companion edit prompt

Applied separately to each accepted light master:

> Edit this exact image into its dark-mode evening companion. Preserve the exact camera, 16:9 framing, crop, negative-space boundary, object geometry, object placement, scale, materials and scene contents. Change only illumination, exposure and colour temperature: quiet night ambience, deep ink and indigo shadows, restrained warm practical highlights, readable silhouettes, no crushed blacks and no added objects. Keep the left reading/heading-safe region low-detail. Do not add text, numbers, people, hands, faces, students, names, school identity, logos, trademarks, watermarks, screens, UI or identifiable locations.

## Release asset evidence

The following table is completed from the final local files after visual acceptance and normalisation; placeholders are release-blocking.

| Slot | Theme | File | Dimensions | Bytes | SHA-256 | Crop / veil | Status |
|---|---|---|---:|---:|---|---|---|
| weekly-operations | light | `weekly-operations-light-v1.webp` | 1600×900 | 40,888 | `ee31eb370732d0b07bdcdfc8473a3ebd960efaa2e3d89987fe07983f867b076a` | right-weighted; shared shell veil | accepted |
| weekly-operations | dark | `weekly-operations-dark-v1.webp` | 1600×900 | 34,966 | `e5d77747248bc2dba5ac349b999493d34ee72aac73d6a9e1ffbf0649b5ab11d7` | same crop; dark shell veil | accepted |
| people-fairness | light | `people-fairness-light-v1.webp` | 1600×900 | 139,966 | `6bc22effce8856ff184a6e778847179b5960c50294bd4265d0f0a032b49f35a8` | right-weighted; shared shell veil | accepted |
| people-fairness | dark | `people-fairness-dark-v1.webp` | 1600×900 | 128,272 | `dc10de06f70140ce2ffe1e9b2f684a07e8b65d4c77e2a02c98505e406b818187` | same crop; dark shell veil | accepted |
| administration-recovery | light | `administration-recovery-light-v1.webp` | 1600×900 | 82,960 | `8d436a0edeac90960c4387386c9f3406225e2adb2018384156efb380096b733b` | right-weighted; shared shell veil | accepted |
| administration-recovery | dark | `administration-recovery-dark-v1.webp` | 1600×900 | 61,108 | `c31c8e2d48ac15f58c6ddaceeb7ee42da342fe442b1c0e2f42f52467a7a782f6` | same crop; dark shell veil | accepted |
| support-lifeline | light | `support-lifeline-light-v1.webp` | 1600×900 | 82,920 | `3aa68bfc45f627e4ef1cc174fe3bc775d28289f0bf7609741c20f66ad18f8e18` | right-weighted; shared shell veil | accepted |
| support-lifeline | dark | `support-lifeline-dark-v1.webp` | 1600×900 | 41,484 | `80ac02a098b640a767ab1af135d012cbc01084affd9f342274f6d1713f870492` | same crop; dark shell veil | accepted |
| devotional | light | `devotional-sacred-light-v2.webp` | 1600×900 | 128,290 | `d1227d719ad8522fa568c3db3551ec65d1595fa92cd1d94478621147d509ce61` | left 58% safe; warm reading veil | accepted |
| devotional | dark | `devotional-sacred-dark-v2.webp` | 1600×900 | 63,704 | `1a995e740cc8414e75b1c864f708c753feccdb5652f085a2d5283a8cc40352f6` | same crop; indigo reading veil | accepted |

Generation date: 2026-07-31. All ten files were visually reviewed at source resolution and again after local normalisation. No forbidden content was observed; the v1 devotional pair was removed from the active asset set after v2 acceptance and remains recoverable through Git history.
