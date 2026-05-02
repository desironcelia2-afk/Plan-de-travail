# PRD — Ateliers Autonomes (Maternelle)

## Problem Statement (original, verbatim)
> Est-il possible de créer une application, dans laquelle il y a une page d'accueil. Sur cette page d'accueil se trouve le prénom des enfants. C'est une application utilisée dans un moment d'atelier autonome en classe, dans une classe de maternelle. Quand un enfant a fini un atelier autonome, il se dirige vers le tableau interactif, il sélectionne son prénom, ça ouvre une page où est listé tous les ateliers autonomes qu'il doit réaliser. Et il va valider celui qu'il vient de réaliser pour ensuite revenir à l'écran d'accueil avec tous les prénoms pour qu'un autre enfant puisse sélectionner son prénom et valider les ateliers qu'il a déjà faits.

## User personas
1. **Enfant de maternelle (3-6 ans)** — non-lecteur : tape sur son prénom (reconnu visuellement via emoji/couleur), valide un atelier par un grand bouton. UX doit être simple, sans geste complexe.
2. **Maîtresse / enseignant(e)** — gère la liste d'enfants et d'ateliers, consulte le suivi global. Accès protégé par mot de passe.

## Core requirements (static)
- Home page = grille de grandes cartes de prénoms (tableau interactif).
- Page enfant = liste des ateliers avec validation visuelle (coche / vert / confettis).
- Retour accueil après validation pour passer à l'enfant suivant.
- Admin protégé par mot de passe (simple).
- Validations conservées en permanence (pas de reset automatique).
- Design kindergarten-friendly : Fredoka/Nunito, couleurs vives pastel, cartes neo-brutalist, cibles tactiles ≥ 80 px.

## Architecture
- **Backend** : FastAPI + MongoDB (Motor). Collections : `children`, `workshops`, `validations`. Auth admin : header `X-Admin-Password`. Seed auto si vide.
- **Frontend** : React 19 + React Router 7 + Tailwind + shadcn/ui + sonner (toasts) + react-confetti + lucide-react.

## Implemented (v1 — Feb 2026)
- ✅ Seed initial (6 enfants, 8 ateliers).
- ✅ Routes `/`, `/enfant/:id`, `/admin`.
- ✅ CRUD enfants & ateliers (admin).
- ✅ Toggle validation atelier (done / un-done) avec confettis.
- ✅ Tableau de suivi (matrice enfants × ateliers) dans l'admin.
- ✅ Login admin avec mot de passe (`maitresse` par défaut, configurable via `ADMIN_PASSWORD`).
- ✅ sessionStorage pour rester connecté sur rafraîchissement.
- ✅ Design neo-brutalist playful (Fredoka, Nunito, cartes chunky, couleurs pastel).

## Implemented (v2 — Photos — Feb 2026)
- ✅ Upload photos pour enfants et ateliers via Emergent object storage.
- ✅ Photo remplace l'emoji quand présente sur home / page enfant / admin.
- ✅ Bouton Camera (upload) + ImageOff (retirer) dans l'admin.
- ✅ Validation format (jpg/png/webp/gif) + taille max 5 Mo.
- ✅ Backend tests : 9/9 pass (upload, download, delete, unauth, oversize, bad format).

## Implemented (v3 — Multi-classes — Feb 2026)
- ✅ Nouvelle entité `Class` (classes collection) avec nom / emoji / couleur.
- ✅ Chaque enfant rattaché à une classe (`class_id`).
- ✅ Les ateliers restent partagés entre toutes les classes (choix utilisateur).
- ✅ Migration auto : création de "Classe par défaut" au démarrage si aucune classe, et backfill des enfants sans class_id.
- ✅ Nouvelle route `/` = ClassPickerPage ; auto-redirige si une seule classe.
- ✅ `/classe/:classId` = grille des prénoms de cette classe.
- ✅ Bouton retour « Classes » dans HomePage, retour vers `/classe/:classId` depuis page enfant.
- ✅ Admin : nouvel onglet « Classes » avec ajout/suppression (protection dernière classe) + sélecteur de classe dans Enfants / Suivi.
- ✅ Cascade delete : supprimer une classe supprime ses enfants et leurs validations.
- ✅ Tests backend multi-classes : 10/10 pass. Tests frontend E2E : 100% pass.

## Backlog / Next tasks
- **P1** — Photos d'enfants (upload avatar au lieu d'emoji) via object storage.
- **P1** — Réinitialisation manuelle "Nouvelle semaine" (reset des validations avec archive historique).
- **P2** — Export PDF / CSV du suivi hebdomadaire.
- **P2** — Statistiques par atelier (quel atelier le moins fait).
- **P2** — Mode plein écran / kiosk lock pour tableau interactif.
- **P3** — Multi-classe (plusieurs enseignants, chaque classe sa liste).
- **P3** — Audio : TTS du prénom au clic pour les non-lecteurs.
