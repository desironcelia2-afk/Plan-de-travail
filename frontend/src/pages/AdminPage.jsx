import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, adminHeaders, setAdminPassword, getAdminPassword, clearAdminPassword } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ArrowLeft, Trash2, Plus, LogOut, Check, X } from "lucide-react";
import { toast } from "sonner";

const CHILD_EMOJIS = ["🦊", "🐻", "🐰", "🦁", "🦄", "🐼", "🐨", "🐸", "🐵", "🦉", "🐯", "🐶", "🐱", "🐹", "🐻‍❄️"];
const CHILD_COLORS = ["#FDE68A", "#BFDBFE", "#FBCFE8", "#FED7AA", "#DDD6FE", "#BBF7D0", "#FECACA", "#A7F3D0"];
const WS_EMOJIS = ["🎨", "🧩", "🧶", "🔤", "🔢", "✂️", "📚", "🧱", "🎵", "🖍️", "🪁", "🧸", "🔍", "🧮"];
const WS_COLORS = ["#FCA5A5", "#93C5FD", "#FDBA74", "#86EFAC", "#C4B5FD", "#F9A8D4", "#FCD34D", "#67E8F9"];

export default function AdminPage() {
  const navigate = useNavigate();
  const [authed, setAuthed] = useState(!!getAdminPassword());
  const [password, setPassword] = useState("");
  const [children, setChildren] = useState([]);
  const [workshops, setWorkshops] = useState([]);
  const [overview, setOverview] = useState(null);

  // forms
  const [newChild, setNewChild] = useState({ name: "", emoji: CHILD_EMOJIS[0], color: CHILD_COLORS[0] });
  const [newWs, setNewWs] = useState({ name: "", emoji: WS_EMOJIS[0], color: WS_COLORS[0] });

  const login = async (e) => {
    e.preventDefault();
    try {
      await api.post("/admin/login", { password });
      setAdminPassword(password);
      setAuthed(true);
      toast.success("Connexion réussie");
    } catch {
      toast.error("Mot de passe incorrect");
    }
  };

  const logout = () => {
    clearAdminPassword();
    setAuthed(false);
    setPassword("");
  };

  const loadAll = async () => {
    try {
      const [c, w, o] = await Promise.all([
        api.get("/children"),
        api.get("/workshops"),
        api.get("/admin/overview", adminHeaders()),
      ]);
      setChildren(c.data);
      setWorkshops(w.data);
      setOverview(o.data);
    } catch (err) {
      if (err.response?.status === 401) {
        logout();
        toast.error("Session expirée, reconnecte-toi.");
      }
    }
  };

  useEffect(() => {
    if (authed) loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed]);

  const addChild = async (e) => {
    e.preventDefault();
    if (!newChild.name.trim()) return toast.error("Prénom requis");
    try {
      await api.post("/children", newChild, adminHeaders());
      setNewChild({ name: "", emoji: CHILD_EMOJIS[0], color: CHILD_COLORS[0] });
      toast.success("Enfant ajouté");
      loadAll();
    } catch {
      toast.error("Erreur à l'ajout");
    }
  };

  const removeChild = async (cid) => {
    if (!window.confirm("Supprimer cet enfant et son historique ?")) return;
    await api.delete(`/children/${cid}`, adminHeaders());
    toast.success("Enfant supprimé");
    loadAll();
  };

  const addWs = async (e) => {
    e.preventDefault();
    if (!newWs.name.trim()) return toast.error("Nom d'atelier requis");
    try {
      await api.post("/workshops", newWs, adminHeaders());
      setNewWs({ name: "", emoji: WS_EMOJIS[0], color: WS_COLORS[0] });
      toast.success("Atelier ajouté");
      loadAll();
    } catch {
      toast.error("Erreur à l'ajout");
    }
  };

  const removeWs = async (wid) => {
    if (!window.confirm("Supprimer cet atelier et toutes ses validations ?")) return;
    await api.delete(`/workshops/${wid}`, adminHeaders());
    toast.success("Atelier supprimé");
    loadAll();
  };

  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" data-testid="admin-login-page">
        <form onSubmit={login} className="kb-card p-8 md:p-10 w-full max-w-md space-y-6" data-testid="admin-login-form">
          <div>
            <h1 className="font-heading font-bold text-4xl mb-2">Espace Maîtresse</h1>
            <p className="text-[#475569] text-lg">Entre le mot de passe pour continuer.</p>
            <p className="text-sm text-[#64748B] mt-1">(par défaut : <code>maitresse</code>)</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="pwd" className="text-lg font-heading">Mot de passe</Label>
            <Input
              id="pwd"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-14 text-xl rounded-2xl border-4 border-[#CBD5E1]"
              data-testid="admin-password-input"
              autoFocus
            />
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={() => navigate("/")} className="kb-btn kb-btn-ghost" data-testid="admin-cancel-btn">
              <ArrowLeft className="w-4 h-4" /> Accueil
            </button>
            <button type="submit" className="kb-btn kb-btn-primary flex-1" data-testid="admin-login-btn">
              Entrer
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 md:px-10 py-8 max-w-6xl mx-auto" data-testid="admin-page">
      <header className="flex items-center justify-between mb-8 gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/")} className="kb-btn kb-btn-back" data-testid="admin-back-btn">
            <ArrowLeft className="w-5 h-5" /> Accueil
          </button>
          <h1 className="font-heading font-bold text-3xl md:text-4xl">Espace Maîtresse</h1>
        </div>
        <button onClick={logout} className="kb-btn kb-btn-ghost" data-testid="logout-btn">
          <LogOut className="w-4 h-4" /> Déconnexion
        </button>
      </header>

      <Tabs defaultValue="children" className="w-full">
        <TabsList className="grid grid-cols-3 w-full max-w-xl mb-6 h-auto bg-white border-4 border-[#CBD5E1] rounded-2xl p-1">
          <TabsTrigger value="children" className="text-base md:text-lg py-3 rounded-xl" data-testid="tab-children">Enfants</TabsTrigger>
          <TabsTrigger value="workshops" className="text-base md:text-lg py-3 rounded-xl" data-testid="tab-workshops">Ateliers</TabsTrigger>
          <TabsTrigger value="overview" className="text-base md:text-lg py-3 rounded-xl" data-testid="tab-overview">Suivi</TabsTrigger>
        </TabsList>

        {/* Children Tab */}
        <TabsContent value="children">
          <form onSubmit={addChild} className="kb-card p-6 mb-6 space-y-4" data-testid="add-child-form">
            <h2 className="font-heading font-bold text-2xl">Ajouter un enfant</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label className="text-base">Prénom</Label>
                <Input
                  value={newChild.name}
                  onChange={(e) => setNewChild({ ...newChild, name: e.target.value })}
                  placeholder="Ex : Léa"
                  className="h-12 text-lg rounded-xl border-2"
                  data-testid="new-child-name"
                />
              </div>
            </div>
            <div>
              <Label className="text-base">Emoji</Label>
              <div className="flex gap-2 flex-wrap mt-1">
                {CHILD_EMOJIS.map((e) => (
                  <button
                    type="button"
                    key={e}
                    onClick={() => setNewChild({ ...newChild, emoji: e })}
                    className={`w-12 h-12 rounded-xl border-4 text-2xl flex items-center justify-center ${
                      newChild.emoji === e ? "border-[#0EA5E9] bg-[#E0F2FE]" : "border-[#CBD5E1] bg-white"
                    }`}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-base">Couleur</Label>
              <div className="flex gap-2 flex-wrap mt-1">
                {CHILD_COLORS.map((c) => (
                  <button
                    type="button"
                    key={c}
                    onClick={() => setNewChild({ ...newChild, color: c })}
                    className={`w-10 h-10 rounded-full border-4 ${newChild.color === c ? "border-[#0F172A]" : "border-white"}`}
                    style={{ backgroundColor: c }}
                    aria-label={c}
                  />
                ))}
              </div>
            </div>
            <button type="submit" className="kb-btn kb-btn-primary" data-testid="add-child-btn">
              <Plus className="w-5 h-5" /> Ajouter
            </button>
          </form>

          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-4" data-testid="children-admin-list">
            {children.map((c) => (
              <div key={c.id} className="kb-card p-5 flex items-center justify-between" style={{ backgroundColor: c.color }}>
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-14 h-14 rounded-full bg-white border-4 border-white flex items-center justify-center text-3xl">
                    {c.emoji}
                  </div>
                  <div className="font-heading font-bold text-xl truncate">{c.name}</div>
                </div>
                <button
                  onClick={() => removeChild(c.id)}
                  className="kb-btn kb-btn-danger"
                  data-testid={`delete-child-${c.name}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </TabsContent>

        {/* Workshops Tab */}
        <TabsContent value="workshops">
          <form onSubmit={addWs} className="kb-card p-6 mb-6 space-y-4" data-testid="add-workshop-form">
            <h2 className="font-heading font-bold text-2xl">Ajouter un atelier</h2>
            <div>
              <Label className="text-base">Nom</Label>
              <Input
                value={newWs.name}
                onChange={(e) => setNewWs({ ...newWs, name: e.target.value })}
                placeholder="Ex : Puzzle"
                className="h-12 text-lg rounded-xl border-2"
                data-testid="new-workshop-name"
              />
            </div>
            <div>
              <Label className="text-base">Icône</Label>
              <div className="flex gap-2 flex-wrap mt-1">
                {WS_EMOJIS.map((e) => (
                  <button
                    type="button"
                    key={e}
                    onClick={() => setNewWs({ ...newWs, emoji: e })}
                    className={`w-12 h-12 rounded-xl border-4 text-2xl flex items-center justify-center ${
                      newWs.emoji === e ? "border-[#0EA5E9] bg-[#E0F2FE]" : "border-[#CBD5E1] bg-white"
                    }`}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-base">Couleur</Label>
              <div className="flex gap-2 flex-wrap mt-1">
                {WS_COLORS.map((c) => (
                  <button
                    type="button"
                    key={c}
                    onClick={() => setNewWs({ ...newWs, color: c })}
                    className={`w-10 h-10 rounded-full border-4 ${newWs.color === c ? "border-[#0F172A]" : "border-white"}`}
                    style={{ backgroundColor: c }}
                    aria-label={c}
                  />
                ))}
              </div>
            </div>
            <button type="submit" className="kb-btn kb-btn-primary" data-testid="add-workshop-btn">
              <Plus className="w-5 h-5" /> Ajouter
            </button>
          </form>

          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-4" data-testid="workshops-admin-list">
            {workshops.map((w) => (
              <div key={w.id} className="kb-card p-5 flex items-center justify-between" style={{ backgroundColor: w.color }}>
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-14 h-14 rounded-2xl bg-white border-4 border-white flex items-center justify-center text-3xl">
                    {w.emoji}
                  </div>
                  <div className="font-heading font-bold text-xl truncate">{w.name}</div>
                </div>
                <button
                  onClick={() => removeWs(w.id)}
                  className="kb-btn kb-btn-danger"
                  data-testid={`delete-workshop-${w.name}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </TabsContent>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="kb-card p-4 md:p-6 overflow-x-auto" data-testid="overview-table">
            {!overview || overview.rows.length === 0 ? (
              <p className="text-lg text-[#475569]">Aucune donnée.</p>
            ) : (
              <table className="w-full border-collapse min-w-[640px]">
                <thead>
                  <tr>
                    <th className="text-left font-heading text-lg p-3 sticky left-0 bg-white">Enfant</th>
                    {overview.workshops.map((w) => (
                      <th key={w.id} className="p-3 font-heading text-base text-center min-w-[90px]">
                        <div className="text-2xl">{w.emoji}</div>
                        <div className="text-sm text-[#475569]">{w.name}</div>
                      </th>
                    ))}
                    <th className="p-3 font-heading text-base text-center">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.rows.map((row) => (
                    <tr key={row.child.id} className="border-t-2 border-[#E2E8F0]">
                      <td className="p-3 sticky left-0 bg-white">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{row.child.emoji}</span>
                          <span className="font-bold">{row.child.name}</span>
                        </div>
                      </td>
                      {overview.workshops.map((w) => {
                        const done = row.done_workshop_ids.includes(w.id);
                        return (
                          <td key={w.id} className="p-3 text-center">
                            {done ? (
                              <Check className="w-6 h-6 mx-auto text-[#22C55E]" strokeWidth={3} />
                            ) : (
                              <X className="w-5 h-5 mx-auto text-[#CBD5E1]" />
                            )}
                          </td>
                        );
                      })}
                      <td className="p-3 text-center font-bold">
                        {row.done_count}/{row.total}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
