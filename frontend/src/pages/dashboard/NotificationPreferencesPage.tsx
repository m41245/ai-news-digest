import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../api";
import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Spinner } from "../../components/ui/Spinner";
import { ErrorState } from "../../components/ui/ErrorState";
import { formatDateTime, cn } from "../../utils";

const COMMON_TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Anchorage",
  "Pacific/Honolulu",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Paris",
  "Europe/Moscow",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Asia/Singapore",
  "Australia/Sydney",
  "Australia/Perth",
  "Pacific/Auckland",
];

type ToastState = { type: "success" | "error"; message: string } | null;

export function NotificationPreferencesPage() {
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<ToastState>(null);

  const { data: pref, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: () => notificationsApi.preferences.get(),
  });

  const { data: schedulePreview, refetch: refetchPreview } = useQuery({
    queryKey: ["notification-schedule-preview"],
    queryFn: () => notificationsApi.schedulePreview(),
    enabled: !!pref,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof notificationsApi.preferences.update>[0]) =>
      notificationsApi.preferences.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-preferences"] });
      void refetchPreview();
      setToast({ type: "success", message: "Preferences saved successfully." });
      setTimeout(() => setToast(null), 4000);
    },
    onError: (err: Error) => {
      setToast({ type: "error", message: err.message ?? "Failed to save preferences." });
      setTimeout(() => setToast(null), 4000);
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => notificationsApi.preferences.reset(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-preferences"] });
      void refetchPreview();
      setToast({ type: "success", message: "Preferences reset to defaults." });
      setTimeout(() => setToast(null), 4000);
    },
    onError: (err: Error) => {
      setToast({ type: "error", message: err.message ?? "Failed to reset preferences." });
      setTimeout(() => setToast(null), 4000);
    },
  });

  if (isLoading) {
    return (
      <>
        <Seo title="Notification Preferences" noindex />
        <div className="container-page py-8">
          <Spinner label="Loading preferences" />
        </div>
      </>
    );
  }

  if (isError || !pref) {
    return (
      <>
        <Seo title="Notification Preferences" noindex />
        <div className="container-page py-8">
          <ErrorState
            message={error?.message ?? "Failed to load preferences."}
            retry={() => void refetch()}
          />
        </div>
      </>
    );
  }

  const quietStart = pref.quiet_hours_start ?? "";
  const quietEnd = pref.quiet_hours_end ?? "";

  const quietHoursValid = useMemo(() => {
    if (!quietStart || !quietEnd) return true;
    if (quietStart === quietEnd) return false;
    return true;
  }, [quietStart, quietEnd]);

  const isOvernight = quietStart !== "" && quietEnd !== "" && quietEnd < quietStart;

  const handleQuietHoursChange = (field: "quiet_hours_start" | "quiet_hours_end", value: string) => {
    const next = { ...pref, [field]: value || null };
    updateMutation.mutate(next);
  };

  return (
    <>
      <Seo title="Notification Preferences" noindex />
      <div className="container-page py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Notification Preferences</h1>
          <p className="mt-1 text-slate-600">
            Configure how and when you receive notifications.
          </p>
        </div>

        {toast && (
          <div
            className={`mb-6 rounded-lg px-4 py-3 text-sm font-medium ${
              toast.type === "success"
                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                : "bg-red-50 text-red-800 border border-red-200"
            }`}
            role="alert"
          >
            {toast.message}
          </div>
        )}

        <div className="space-y-6">
          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Delivery Channels</h2>
            <p className="mt-1 text-sm text-slate-500">
              Choose where you want to receive notifications.
            </p>
            <div className="mt-4 space-y-4">
              <ToggleField
                label="In-app notifications"
                description="Show notifications inside the application. These appear in the notification bell."
                checked={pref.in_app_enabled}
                onChange={(checked) =>
                  updateMutation.mutate({ in_app_enabled: checked })
                }
                disabled={updateMutation.isPending}
              />
              <ToggleField
                label="Email notifications"
                description="Receive notifications via email. Email delivery may be deferred during quiet hours."
                checked={pref.email_enabled}
                onChange={(checked) =>
                  updateMutation.mutate({ email_enabled: checked })
                }
                disabled={updateMutation.isPending}
              />
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Digest Notifications</h2>
            <p className="mt-1 text-sm text-slate-500">
              Get notified when new digests are available.
            </p>
            <div className="mt-4 space-y-4">
              <ToggleField
                label="Daily digest ready"
                description="Notify when a new daily digest is available."
                checked={pref.daily_digest_enabled}
                onChange={(checked) =>
                  updateMutation.mutate({ daily_digest_enabled: checked })
                }
                disabled={updateMutation.isPending}
              />
              <ToggleField
                label="Weekly digest ready"
                description="Notify when a new weekly digest is available."
                checked={pref.weekly_digest_enabled}
                onChange={(checked) =>
                  updateMutation.mutate({ weekly_digest_enabled: checked })
                }
                disabled={updateMutation.isPending}
              />
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Notification Types</h2>
            <p className="mt-1 text-sm text-slate-500">
              Choose which types of notifications you want to receive.
            </p>
            <div className="mt-4 space-y-4">
              <ToggleField
                label="Followed company updates"
                description="Get notified when there is new intelligence about companies you follow."
                checked={pref.notify_followed_companies}
                onChange={(checked) =>
                  updateMutation.mutate({ notify_followed_companies: checked })
                }
                disabled={updateMutation.isPending}
              />
              <ToggleField
                label="Followed topic updates"
                description="Get notified when there is new intelligence about topics you follow."
                checked={pref.notify_followed_topics}
                onChange={(checked) =>
                  updateMutation.mutate({ notify_followed_topics: checked })
                }
                disabled={updateMutation.isPending}
              />
              <ToggleField
                label="Story evolution alerts"
                description="Get notified when followed stories have meaningful new developments."
                checked={pref.notify_story_evolution}
                onChange={(checked) =>
                  updateMutation.mutate({ notify_story_evolution: checked })
                }
                disabled={updateMutation.isPending}
              />
              <ToggleField
                label="Contradiction and correction alerts"
                description="Get notified when contradictions or corrections are detected."
                checked={pref.notify_corrections}
                onChange={(checked) =>
                  updateMutation.mutate({ notify_corrections: checked })
                }
                disabled={updateMutation.isPending}
              />
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Quiet Hours</h2>
            <p className="mt-1 text-sm text-slate-500">
              Pause email notifications during these hours. In-app notifications are always delivered.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TimeField
                label="Start time"
                description="When quiet hours begin"
                value={quietStart}
                onChange={(value) => handleQuietHoursChange("quiet_hours_start", value)}
                disabled={updateMutation.isPending}
              />
              <TimeField
                label="End time"
                description="When quiet hours end"
                value={quietEnd}
                onChange={(value) => handleQuietHoursChange("quiet_hours_end", value)}
                disabled={updateMutation.isPending}
              />
            </div>
            {quietStart && quietEnd && (
              <div className="mt-3">
                {isOvernight ? (
                  <p className="text-xs text-amber-700 bg-amber-50 rounded-md px-3 py-2">
                    Quiet hours span overnight (from {quietStart} to {quietEnd} the next day).
                  </p>
                ) : (
                  <p className="text-xs text-emerald-700 bg-emerald-50 rounded-md px-3 py-2">
                    Quiet hours run from {quietStart} to {quietEnd}.
                  </p>
                )}
                {!quietHoursValid && (
                  <p className="mt-1 text-xs text-red-600">
                    Start and end times cannot be identical. Please choose different times.
                  </p>
                )}
              </div>
            )}
            <div className="mt-4">
              <label htmlFor="timezone" className="block font-medium text-slate-900">
                Timezone
              </label>
              <p className="text-sm text-slate-500">
                Used to calculate quiet hours and schedule preview.
              </p>
              <select
                id="timezone"
                value={pref.timezone}
                onChange={(e) => updateMutation.mutate({ timezone: e.target.value })}
                disabled={updateMutation.isPending}
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50"
              >
                {COMMON_TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Schedule Preview</h2>
            <p className="mt-1 text-sm text-slate-500">
              When your next notifications would be sent based on your current preferences and timezone.
            </p>
            {schedulePreview && schedulePreview.next_notification_times.length > 0 ? (
              <ul className="mt-4 space-y-2">
                {schedulePreview.next_notification_times.map((item) => (
                  <li
                    key={item.notification_type}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-900 capitalize">
                        {item.notification_type.replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-slate-500">{item.reason}</p>
                    </div>
                    <p className="text-sm text-slate-700">
                      {formatDateTime(item.scheduled_for)}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-slate-500">No upcoming scheduled notifications.</p>
            )}
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-slate-900">Thresholds and Limits</h2>
            <p className="mt-1 text-sm text-slate-500">
              Fine-tune when you receive notifications to reduce noise.
            </p>
            <div className="mt-4 space-y-4">
              <NumberField
                label="Minimum importance threshold"
                description="Only notify for stories with importance at or above this value (0 to 1)."
                value={pref.min_importance}
                min={0}
                max={1}
                step={0.1}
                onChange={(value) =>
                  updateMutation.mutate({ min_importance: value })
                }
                disabled={updateMutation.isPending}
              />
              <NumberField
                label="Minimum confidence threshold"
                description="Only notify for stories with confidence at or above this value (0 to 1)."
                value={pref.min_confidence}
                min={0}
                max={1}
                step={0.1}
                onChange={(value) =>
                  updateMutation.mutate({ min_confidence: value })
                }
                disabled={updateMutation.isPending}
              />
              <NumberField
                label="Maximum notifications per day"
                description="Cap the number of notifications you receive each day. Range: 1 to 100."
                value={pref.max_per_day}
                min={1}
                max={100}
                step={1}
                onChange={(value) =>
                  updateMutation.mutate({ max_per_day: Math.min(100, Math.max(1, value)) })
                }
                disabled={updateMutation.isPending}
              />
            </div>
          </Card>

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button
              variant="ghost"
              onClick={() => resetMutation.mutate()}
              disabled={resetMutation.isPending}
            >
              Reset to defaults
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

function ToggleField({
  label,
  description,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="font-medium text-slate-900">{label}</p>
        <p className="text-sm text-slate-500">{description}</p>
      </div>
      <button
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2",
          checked ? "bg-brand-600" : "bg-slate-200",
          disabled ? "opacity-50 cursor-not-allowed" : "",
        )}
      >
        <span
          className={cn(
            "inline-block h-5 w-5 rounded-full bg-white shadow transform transition duration-200 ease-in-out",
            checked ? "translate-x-5" : "translate-x-0",
          )}
        />
      </button>
    </div>
  );
}

function NumberField({
  label,
  description,
  value,
  min,
  max,
  step,
  onChange,
  disabled,
}: {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  disabled: boolean;
}) {
  return (
    <div>
      <label className="block font-medium text-slate-900">{label}</label>
      <p className="text-sm text-slate-500">{description}</p>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        aria-describedby={`${label}-desc`}
        onChange={(e) => {
          const parsed = parseFloat(e.target.value);
          if (!Number.isNaN(parsed)) {
            onChange(parsed);
          }
        }}
        className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50"
      />
    </div>
  );
}

function TimeField({
  label,
  description,
  value,
  onChange,
  disabled,
}: {
  label: string;
  description: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <div>
      <label className="block font-medium text-slate-900">{label}</label>
      <p className="text-sm text-slate-500">{description}</p>
      <input
        type="time"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50"
      />
    </div>
  );
}
