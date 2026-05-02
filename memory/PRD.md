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
- ✅ 100 % des tests backend et frontend passent (iteration_1).

## Backlog / Next tasks
- **P1** — Photos d'enfants (upload avatar au lieu d'emoji) via object storage.
- **P1** — Réinitialisation manuelle "Nouvelle semaine" (reset des validations avec archive historique).
- **P2** — Export PDF / CSV du suivi hebdomadaire.
- **P2** — Statistiques par atelier (quel atelier le moins fait).
- **P2** — Mode plein écran / kiosk lock pour tableau interactif.
- **P3** — Multi-classe (plusieurs enseignants, chaque classe sa liste).
- **P3** — Audio : TTS du prénom au clic pour les non-lecteurs.
