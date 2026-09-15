import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { userPreferenceApi, publicApi } from "../../api";
import type {
  UserPreferenceResponse,
  Company,
  Topic,
  Category,
  Source,
} from "../../types";

export function PreferencesPage() {
  const [preferences, setPreferences] = useState<UserPreferenceResponse | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const [form, setForm] = useState({
    min_importance: 0.0,
    min_confidence: 0.0,
    feed_sort: "published_at" as string,
    freshness_window_days: undefined as number | undefined,
    preferred_source_types: [] as string[],
  });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [prefs, comps, tops, cats, srcs] = await Promise.all([
          userPreferenceApi.get(),
          publicApi.companies(),
          publicApi.topics(),
          publicApi.categories(),
          publicApi.sources(),
        ]);
        if (!cancelled) {
          setPreferences(prefs);
          setCompanies(comps);
          setTopics(tops);
          setCategories(cats);
          setSources(srcs);
          setForm({
            min_importance: prefs.min_importance,
            min_confidence: prefs.min_confidence,
            feed_sort: prefs.feed_sort,
            freshness_window_days: prefs.freshness_window_days ?? undefined,
            preferred_source_types: prefs.preferred_source_types,
          });
        }
      } catch (e) {
        if (!cancelled) setError("Failed to load preferences.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleFollow = async (type: "company" | "topic" | "category" | "source", id: string, slug?: string) => {
    if (!preferences) return;
    const isFollowed =
      type === "company" && preferences.followed_companies.includes(id) ||
      type === "topic" && preferences.followed_topics.includes(id) ||
      type === "category" && preferences.followed_categories.includes(id) ||
      type === "source" && preferences.followed_sources.includes(id);

    try {
      if (isFollowed) {
        if (type === "company" && slug) await userPreferenceApi.unfollowCompany(slug);
        else if (type === "topic" && slug) await userPreferenceApi.unfollowTopic(slug);
        else if (type === "category") await userPreferenceApi.unfollowCategory(id);
        else if (type === "source") await userPreferenceApi.unfollowSource(id);
      } else {
        if (type === "company" && slug) await userPreferenceApi.followCompany(slug);
        else if (type === "topic" && slug) await userPreferenceApi.followTopic(slug);
        else if (type === "category") await userPreferenceApi.followCategory(id);
        else if (type === "source") await userPreferenceApi.followSource(id);
      }
      setPreferences((p: UserPreferenceResponse | null) => p && { ...p });
    } catch {
      setError("Failed to update preference.");
    }
  };

  const toggleMute = async (type: "company" | "topic" | "category" | "source", id: string, slug?: string) => {
    if (!preferences) return;
    const isMuted =
      type === "company" && preferences.muted_companies.includes(id) ||
      type === "topic" && preferences.muted_topics.includes(id) ||
      type === "category" && preferences.muted_categories.includes(id) ||
      type === "source" && preferences.muted_sources.includes(id);

    try {
      if (isMuted) {
        if (type === "company" && slug) await userPreferenceApi.unmuteCompany(slug);
        else if (type === "topic" && slug) await userPreferenceApi.unmuteTopic(slug);
        else if (type === "category") await userPreferenceApi.unmuteCategory(id);
        else if (type === "source") await userPreferenceApi.unmuteSource(id);
      } else {
        if (type === "company" && slug) await userPreferenceApi.muteCompany(slug);
        else if (type === "topic" && slug) await userPreferenceApi.muteTopic(slug);
        else if (type === "category") await userPreferenceApi.muteCategory(id);
        else if (type === "source") await userPreferenceApi.muteSource(id);
      }
      setPreferences((p: UserPreferenceResponse | null) => p && { ...p });
    } catch {
      setError("Failed to update mute preference.");
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const updated = await userPreferenceApi.update(form);
      setPreferences(updated);
    } catch {
      setError("Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  const resetPreferences = async () => {
    if (!confirm("Reset all preferences to defaults?")) return;
    try {
      await userPreferenceApi.reset();
      setPreferences(null);
      navigate("/me");
    } catch {
      setError("Failed to reset preferences.");
    }
  };

  if (loading) return <div className="p-6">Loading preferences...</div>;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!preferences) return <div className="p-6">No preferences found.</div>;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-6 text-2xl font-bold">Your Preferences</h1>

      <section className="mb-8 rounded border p-4">
        <h2 className="mb-4 text-xl font-semibold">Feed Settings</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col">
            <span className="mb-1 text-sm font-medium">Minimum Importance</span>
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={form.min_importance}
              onChange={(e) => setForm({ ...form, min_importance: parseFloat(e.target.value) })}
              className="rounded border px-3 py-2"
            />
          </label>
          <label className="flex flex-col">
            <span className="mb-1 text-sm font-medium">Minimum Confidence</span>
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={form.min_confidence}
              onChange={(e) => setForm({ ...form, min_confidence: parseFloat(e.target.value) })}
              className="rounded border px-3 py-2"
            />
          </label>
          <label className="flex flex-col">
            <span className="mb-1 text-sm font-medium">Feed Sort</span>
            <select
              value={form.feed_sort}
              onChange={(e) => setForm({ ...form, feed_sort: e.target.value })}
              className="rounded border px-3 py-2"
            >
              <option value="published_at">Published At</option>
              <option value="importance">Importance</option>
              <option value="relevance">Relevance</option>
            </select>
          </label>
          <label className="flex flex-col">
            <span className="mb-1 text-sm font-medium">Freshness Window (days, optional)</span>
            <input
              type="number"
              min="1"
              value={form.freshness_window_days ?? ""}
              onChange={(e) =>
                setForm({ ...form, freshness_window_days: e.target.value ? parseInt(e.target.value) : undefined })
              }
              className="rounded border px-3 py-2"
            />
          </label>
        </div>
        <div className="mt-4 flex gap-2">
          <button
            onClick={saveSettings}
            disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
          <button
            onClick={resetPreferences}
            className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
          >
            Reset All Preferences
          </button>
        </div>
      </section>

      <EntitySection
        title="Companies"
        items={companies}
        followedIds={preferences.followed_companies}
        mutedIds={preferences.muted_companies}
        onToggleFollow={(id) => toggleFollow("company", id, companies.find((c) => c.id === id)?.name.toLowerCase())}
        onToggleMute={(id) => toggleMute("company", id, companies.find((c) => c.id === id)?.name.toLowerCase())}
        getId={(c) => c.id}
        getName={(c) => c.name}
      />

      <EntitySection
        title="Topics"
        items={topics}
        followedIds={preferences.followed_topics}
        mutedIds={preferences.muted_topics}
        onToggleFollow={(id) => toggleFollow("topic", id, topics.find((t) => t.id === id)?.name.toLowerCase())}
        onToggleMute={(id) => toggleMute("topic", id, topics.find((t) => t.id === id)?.name.toLowerCase())}
        getId={(t) => t.id}
        getName={(t) => t.name}
      />

      <EntitySection
        title="Categories"
        items={categories}
        followedIds={preferences.followed_categories}
        mutedIds={preferences.muted_categories}
        onToggleFollow={(id) => toggleFollow("category", id)}
        onToggleMute={(id) => toggleMute("category", id)}
        getId={(c) => c.id}
        getName={(c) => c.name}
      />

      <EntitySection
        title="Sources"
        items={sources}
        followedIds={preferences.followed_sources}
        mutedIds={preferences.muted_sources}
        onToggleFollow={(id) => toggleFollow("source", id)}
        onToggleMute={(id) => toggleMute("source", id)}
        getId={(s) => s.id}
        getName={(s) => s.name}
      />
    </div>
  );
}

interface EntitySectionProps<T> {
  title: string;
  items: T[];
  followedIds: string[];
  mutedIds: string[];
  onToggleFollow: (id: string) => void;
  onToggleMute: (id: string) => void;
  getId: (item: T) => string;
  getName: (item: T) => string;
}

function EntitySection<T>({ title, items, followedIds, mutedIds, onToggleFollow, onToggleMute, getId, getName }: EntitySectionProps<T>) {
  return (
    <section className="mb-8 rounded border p-4">
      <h2 className="mb-4 text-xl font-semibold">{title}</h2>
      {items.length === 0 ? (
        <p className="text-gray-500">No {title.toLowerCase()} available.</p>
      ) : (
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const id = getId(item);
            const name = getName(item);
            const isFollowed = followedIds.includes(id);
            const isMuted = mutedIds.includes(id);
            return (
              <div
                key={id}
                className="flex items-center justify-between rounded border p-2"
              >
                <span className="truncate">{name}</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => onToggleFollow(id)}
                    className={`rounded px-2 py-1 text-sm ${
                      isFollowed
                        ? "bg-green-600 text-white hover:bg-green-700"
                        : "bg-gray-200 hover:bg-gray-300"
                    }`}
                  >
                    {isFollowed ? "Following" : "Follow"}
                  </button>
                  <button
                    onClick={() => onToggleMute(id)}
                    className={`rounded px-2 py-1 text-sm ${
                      isMuted
                        ? "bg-red-600 text-white hover:bg-red-700"
                        : "bg-gray-200 hover:bg-gray-300"
                    }`}
                  >
                    {isMuted ? "Muted" : "Mute"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
