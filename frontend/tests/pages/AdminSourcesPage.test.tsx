import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "../../src/auth/AuthContext";
import { AdminSourcesPage } from "../../src/pages/admin/AdminSourcesPage";
import * as api from "../../src/api";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <HelmetProvider>
        <AuthProvider>
          <MemoryRouter>
            <AdminSourcesPage />
          </MemoryRouter>
        </AuthProvider>
      </HelmetProvider>
    </QueryClientProvider>,
  );
}

const baseSource = {
  id: "1",
  name: "Source A",
  feed_url: "https://example.com/feed.xml",
  website_url: null,
  description: null,
  is_active: true,
  status: "verified",
};

describe("AdminSourcesPage toggle", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.spyOn(api.sourcesApi, "list").mockResolvedValue({
      items: [baseSource],
      total: 1,
      limit: 100,
      offset: 0,
    } as any);
    vi.spyOn(api.sourcesApi, "approve").mockResolvedValue({
      id: "1",
      name: "Source A",
      feed_url: "https://example.com/feed.xml",
      is_active: true,
      status: "verified",
      decision: "APPROVE",
      previous_status: "verified",
      previous_is_active: false,
      reason: "Approved by administrator",
      changed: true,
    } as any);
    vi.spyOn(api.sourcesApi, "deactivate").mockResolvedValue({
      id: "1",
      name: "Source A",
      feed_url: "https://example.com/feed.xml",
      is_active: false,
      status: "verified",
      decision: "DEACTIVATE",
      previous_status: "verified",
      previous_is_active: true,
      reason: "Disabled by administrator",
      changed: true,
    } as any);
    vi.spyOn(api.sourcesApi, "update").mockResolvedValue({} as any);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses deactivate endpoint when disabling an active source", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Source A")).toBeInTheDocument());
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /disable/i }));
    await waitFor(() =>
      expect(api.sourcesApi.deactivate).toHaveBeenCalledWith("1", {
        reason: "Disabled by administrator",
      }),
    );
    expect(api.sourcesApi.update).not.toHaveBeenCalledWith(
      "1",
      expect.objectContaining({ is_active: expect.anything() }),
    );
  });

  it("uses approve endpoint when enabling an inactive source", async () => {
    vi.spyOn(api.sourcesApi, "list").mockResolvedValue({
      items: [{ ...baseSource, is_active: false, status: "pending_review" }],
      total: 1,
      limit: 100,
      offset: 0,
    } as any);
    renderPage();
    await waitFor(() => expect(screen.getByText("Source A")).toBeInTheDocument());
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /enable/i }));
    await waitFor(() =>
      expect(api.sourcesApi.approve).toHaveBeenCalledWith("1", {
        reason: "Approved by administrator",
      }),
    );
    expect(api.sourcesApi.update).not.toHaveBeenCalled();
  });

  it("shows loading state while action is pending", async () => {
    let resolveDeactivate: (v: unknown) => void;
    vi.spyOn(api.sourcesApi, "deactivate").mockReturnValue(
      new Promise((resolve) => {
        resolveDeactivate = resolve;
      }) as any,
    );
    renderPage();
    await waitFor(() => expect(screen.getByText("Source A")).toBeInTheDocument());
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /disable/i }));
    await waitFor(() => expect(screen.getByText("Working…")).toBeInTheDocument());
    resolveDeactivate!({
      id: "1",
      name: "Source A",
      is_active: false,
      status: "verified",
      decision: "DEACTIVATE",
      previous_status: "verified",
      previous_is_active: true,
      reason: "Disabled by administrator",
      changed: true,
    });
    await waitFor(() => expect(screen.queryByText("Working…")).not.toBeInTheDocument());
  });

  it("shows error and no success when action fails", async () => {
    vi.spyOn(api.sourcesApi, "deactivate").mockRejectedValue(
      new Error("You do not have permission to access this resource."),
    );
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    renderPage();
    await waitFor(() => expect(screen.getByText("Source A")).toBeInTheDocument());
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /disable/i }));
    await waitFor(() =>
      expect(
        screen.getByText("You do not have permission to access this resource."),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("Source updated successfully.")).not.toBeInTheDocument();
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("shows success when action succeeds", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Source A")).toBeInTheDocument());
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /disable/i }));
    await waitFor(() =>
      expect(screen.getByText("Source updated successfully.")).toBeInTheDocument(),
    );
  });
});
