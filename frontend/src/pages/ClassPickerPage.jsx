import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Lock, Sparkles, Plus } from "lucide-react";

export default function ClassPickerPage() {
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/classes")
      .then((res) => {
        setClasses(res.data);
        // Auto-redirect to single class
        if (res.data.length === 1) {
          navigate(`/classe/${res.data[0].id}`, { replace: true });
        }
      })
      .catch(() => setClasses([]))
      .finally(() => setLoading(false));
  }, [navigate]);

  return (
    <div className="min-h-screen px-6 md:px-12 py-10" data-testid="class-picker-page">
      <header className="flex items-center justify-between mb-10 md:mb-14">
        <div className="flex items-center gap-3">
          <Sparkles className="w-8 h-8 md:w-10 md:h-10 text-[#F59E0B]" strokeWidth={2.5} />
          <h1 className="font-heading font-bold text-3xl md:text-5xl text-[#0F172A]" data-testid="class-picker-title">
            Mes ateliers
          </h1>
        </div>
        <Link to="/admin" className="kb-btn kb-btn-ghost" data-testid="admin-link">
          <Lock className="w-4 h-4" />
          Maîtresse
        </Link>
      </header>

      <p className="font-heading text-2xl md:text-3xl text-[#475569] mb-8" data-testid="class-picker-instruction">
        Choisis ta classe 👇
      </p>

      {loading ? (
        <div className="text-center text-xl text-[#64748B]">Chargement…</div>
      ) : classes.length === 0 ? (
        <div className="kb-card p-10 text-center max-w-xl mx-auto" data-testid="empty-classes">
          <p className="text-2xl font-heading mb-4">Aucune classe configurée</p>
          <button
            onClick={() => navigate("/admin")}
            className="kb-btn kb-btn-primary"
            data-testid="go-admin-btn"
          >
            <Plus className="w-5 h-5" /> Créer une classe
          </button>
        </div>
      ) : (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 md:gap-8 max-w-6xl mx-auto"
          data-testid="classes-grid"
        >
          {classes.map((k, idx) => (
            <button
              key={k.id}
              onClick={() => navigate(`/classe/${k.id}`)}
              className="kb-card p-8 flex flex-col items-center text-center animate-fade-up"
              style={{ backgroundColor: k.color, animationDelay: `${idx * 50}ms` }}
              data-testid={`class-card-${k.name}`}
            >
              <div
                className="w-28 h-28 md:w-36 md:h-36 rounded-3xl bg-white border-4 border-white shadow-lg flex items-center justify-center text-7xl md:text-8xl mb-5"
                aria-hidden
              >
                {k.emoji}
              </div>
              <div className="font-heading font-bold text-2xl md:text-3xl text-[#0F172A]">
                {k.name}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
