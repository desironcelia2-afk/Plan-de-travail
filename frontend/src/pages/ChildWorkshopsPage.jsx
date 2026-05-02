import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft, Check, Home as HomeIcon } from "lucide-react";
import Confetti from "react-confetti";
import { toast } from "sonner";

export default function ChildWorkshopsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [child, setChild] = useState(null);
  const [statuses, setStatuses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confettiOn, setConfettiOn] = useState(false);
  const [dim, setDim] = useState({ w: window.innerWidth, h: window.innerHeight });

  useEffect(() => {
    const onResize = () => setDim({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const load = async () => {
    try {
      const [c, s] = await Promise.all([
        api.get(`/children/${id}`),
        api.get(`/children/${id}/status`),
      ]);
      setChild(c.data);
      setStatuses(s.data);
    } catch {
      toast.error("Impossible de charger les données");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const toggle = async (ws, done) => {
    try {
      if (done) {
        await api.delete(`/validations`, { params: { child_id: id, workshop_id: ws.id } });
        toast("Atelier remis à faire", { icon: "↩️" });
      } else {
        await api.post(`/validations`, { child_id: id, workshop_id: ws.id });
        setConfettiOn(true);
        setTimeout(() => setConfettiOn(false), 3500);
        toast.success(`Bravo ${child?.name} ! ${ws.emoji} ${ws.name}`);
      }
      // Optimistic update
      setStatuses((prev) =>
        prev.map((s) => (s.workshop.id === ws.id ? { ...s, done: !done } : s))
      );
    } catch {
      toast.error("Erreur lors de la validation");
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-2xl">Chargement…</div>;
  }

  if (!child) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6">
        <p className="text-2xl">Enfant introuvable</p>
        <button className="kb-btn kb-btn-primary" onClick={() => navigate("/")}>Retour</button>
      </div>
    );
  }

  const doneCount = statuses.filter((s) => s.done).length;

  return (
    <div className="min-h-screen px-4 md:px-10 py-8" data-testid="child-page">
      {confettiOn && (
        <Confetti width={dim.w} height={dim.h} numberOfPieces={220} recycle={false} gravity={0.25} />
      )}

      <div className="flex items-center justify-between mb-8 gap-4 flex-wrap">
        <button
          onClick={() => navigate("/")}
          className="kb-btn kb-btn-back"
          data-testid="back-home-btn"
        >
          <ArrowLeft className="w-5 h-5" />
          <HomeIcon className="w-5 h-5" />
          Accueil
        </button>

        <div className="flex items-center gap-4">
          <div
            className="w-16 h-16 md:w-20 md:h-20 rounded-full border-4 border-white shadow-lg flex items-center justify-center text-4xl md:text-5xl"
            style={{ backgroundColor: child.color }}
            aria-hidden
          >
            {child.emoji}
          </div>
          <div>
            <div className="font-heading font-bold text-3xl md:text-5xl text-[#0F172A]" data-testid="child-name">
              {child.name}
            </div>
            <div className="text-lg md:text-xl text-[#475569]" data-testid="done-count">
              {doneCount} / {statuses.length} ateliers validés
            </div>
          </div>
        </div>
      </div>

      {statuses.length === 0 ? (
        <div className="kb-card p-10 text-center max-w-xl mx-auto">
          <p className="text-2xl font-heading mb-2">Aucun atelier</p>
          <p className="text-lg text-[#475569]">
            La maîtresse peut ajouter des ateliers depuis l'admin.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-5 max-w-4xl mx-auto" data-testid="workshops-list">
          {statuses.map((s, idx) => (
            <button
              key={s.workshop.id}
              onClick={() => toggle(s.workshop, s.done)}
              className="kb-card p-5 md:p-7 flex items-center justify-between gap-4 text-left animate-fade-up"
              style={{
                animationDelay: `${idx * 50}ms`,
                backgroundColor: s.done ? "#DCFCE7" : "#FFFFFF",
                borderColor: s.done ? "#86EFAC" : "var(--border)",
                boxShadow: s.done ? "0 8px 0 #86EFAC" : "0 8px 0 var(--border)",
              }}
              data-testid={`workshop-row-${s.workshop.id}`}
            >
              <div className="flex items-center gap-5 flex-1 min-w-0">
                <div
                  className="w-20 h-20 md:w-24 md:h-24 rounded-3xl border-4 border-white shadow-md flex items-center justify-center text-5xl md:text-6xl flex-shrink-0"
                  style={{ backgroundColor: s.workshop.color }}
                  aria-hidden
                >
                  {s.workshop.emoji}
                </div>
                <div className="min-w-0">
                  <div className="font-heading font-bold text-2xl md:text-4xl truncate">
                    {s.workshop.name}
                  </div>
                  <div className="text-base md:text-lg text-[#475569]">
                    {s.done ? "✅ Déjà fait — clique pour annuler" : "Clique pour valider"}
                  </div>
                </div>
              </div>

              <div
                className={`w-20 h-20 md:w-24 md:h-24 rounded-full border-4 flex items-center justify-center flex-shrink-0 transition-colors ${
                  s.done
                    ? "bg-[#22C55E] border-[#16A34A]"
                    : "bg-white border-[#CBD5E1]"
                }`}
                data-testid={`validate-indicator-${s.workshop.id}`}
              >
                {s.done ? (
                  <Check className="w-12 h-12 md:w-14 md:h-14 text-white animate-pop" strokeWidth={4} />
                ) : (
                  <div className="w-8 h-8 rounded-full border-4 border-[#CBD5E1]" />
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
