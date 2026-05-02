import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, photoSrc } from "@/lib/api";
import { Lock, Sparkles, ArrowLeft } from "lucide-react";

export default function HomePage() {
  const { classId } = useParams();
  const [children, setChildren] = useState([]);
  const [klass, setKlass] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      api.get(`/classes/${classId}`),
      api.get(`/children`, { params: { class_id: classId } }),
    ])
      .then(([c, ch]) => {
        setKlass(c.data);
        setChildren(ch.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [classId]);

  return (
    <div className="min-h-screen px-6 md:px-12 py-10" data-testid="home-page">
      <header className="flex items-center justify-between mb-10 md:mb-14 gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => navigate("/")}
            className="kb-btn kb-btn-back"
            data-testid="back-classes-btn"
          >
            <ArrowLeft className="w-5 h-5" />
            Classes
          </button>
          <Sparkles className="w-8 h-8 md:w-10 md:h-10 text-[#F59E0B]" strokeWidth={2.5} />
          <h1 className="font-heading font-bold text-3xl md:text-5xl text-[#0F172A]" data-testid="home-title">
            {klass ? (
              <span className="flex items-center gap-3">
                <span className="text-5xl md:text-6xl">{klass.emoji}</span>
                {klass.name}
              </span>
            ) : (
              "Mes ateliers"
            )}
          </h1>
        </div>
        <Link to="/admin" className="kb-btn kb-btn-ghost" data-testid="admin-link">
          <Lock className="w-4 h-4" />
          Maîtresse
        </Link>
      </header>

      <p className="font-heading text-2xl md:text-3xl text-[#475569] mb-8" data-testid="home-instruction">
        Choisis ton prénom 👇
      </p>

      {loading ? (
        <div className="text-center text-xl text-[#64748B]">Chargement…</div>
      ) : children.length === 0 ? (
        <div className="kb-card p-10 text-center max-w-xl mx-auto" data-testid="empty-children">
          <p className="text-2xl font-heading mb-4">Aucun enfant dans cette classe</p>
          <p className="text-lg text-[#475569] mb-6">
            La maîtresse peut ajouter les prénoms depuis l'espace admin.
          </p>
          <button
            onClick={() => navigate("/admin")}
            className="kb-btn kb-btn-primary"
            data-testid="go-admin-btn"
          >
            Aller à l'admin
          </button>
        </div>
      ) : (
        <div
          className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6 md:gap-8"
          data-testid="children-grid"
        >
          {children.map((c, idx) => (
            <button
              key={c.id}
              onClick={() => navigate(`/enfant/${c.id}`)}
              className="kb-card p-6 md:p-8 flex flex-col items-center text-center animate-fade-up"
              style={{ backgroundColor: c.color, animationDelay: `${idx * 40}ms` }}
              data-testid={`child-card-${c.name}`}
            >
              <div
                className="w-24 h-24 md:w-32 md:h-32 rounded-full bg-white border-4 border-white shadow-lg flex items-center justify-center text-6xl md:text-7xl mb-4 overflow-hidden"
                aria-hidden
              >
                {c.photo_url ? (
                  <img
                    src={photoSrc(c.photo_url)}
                    alt=""
                    className="w-full h-full object-cover"
                    draggable={false}
                  />
                ) : (
                  c.emoji
                )}
              </div>
              <div className="font-heading font-bold text-3xl md:text-4xl text-[#0F172A]">
                {c.name}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
