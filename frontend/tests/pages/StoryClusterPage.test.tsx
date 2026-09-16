// Frontend tests for the M95 StoryClusterPage.

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "../../src/auth/AuthContext";
import { StoryClusterPage } from "../../src/pages/public/StoryClusterPage";
import * as api from "../../src/api";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderWithProviders(ui: React.ReactElement, slug = "test-story") {
  return render(
    <QueryClientProvider client={queryClient}>
      <HelmetProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[`/stories/${slug}`]}>
            <Routes>
              <Route path="/stories/:slug" element={ui} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </HelmetProvider>
    </QueryClientProvider>,
  );
}

describe("StoryClusterPage", () => {
  let spy: ReturnType<typeof vi.spyOn> | null = null;

  afterEach(() => {
    queryClient.clear();
    if (spy) {
      spy.mockRestore();
      spy = null;
    }
  });

  it("shows loading skeleton initially", () => {
    spy = vi.spyOn(api.publicApi, "storyClusterBrief").mockReturnValue(
      new Promise(() => {}),
    ) as unknown as ReturnType<typeof vi.fn>;
    renderWithProviders(<StoryClusterPage />);
    expect(document.querySelector(".container-page")).toBeTruthy();
  });

  it("shows error state on failure", async () => {
    spy = vi.spyOn(api.publicApi, "storyClusterBrief").mockRejectedValueOnce(
      new Error("Network error"),
    ) as unknown as ReturnType<typeof vi.fn>;
    renderWithProviders(<StoryClusterPage />);
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeTruthy();
    });
  });

  it("renders story brief when loaded", async () => {
    spy = vi.spyOn(api.publicApi, "storyClusterBrief").mockResolvedValueOnce({
      id: "1",
      title: "Test Story",
      slug: "test-story",
      status: "ACTIVE",
      article_count: 2,
      source_count: 1,
      independent_source_count: 1,
      summary: "Test summary",
      key_takeaways: ["Takeaway 1"],
      why_it_matters: "This matters",
      activity_status: "developing",
      activity_score: 0.5,
      latest_activity_at: "2026-09-01T00:00:00Z",
      sources: [
        {
          publisher: "Tech Daily",
          source_type: "tech_publication",
          source_role: "Primary",
          article_count: 2,
          provenance_source: "deterministic",
          articles: [
            {
              headline: "Article 1",
              publication_date: "2026-09-01T00:00:00Z",
              url: "https://example.com/1",
              source_id: "source-1",
            },
          ],
        },
      ],
      claims: [],
      conflicts: [],
      timeline: [],
      story_evolution: null,
      trends: [],
      entities: { companies: [], topics: [], graph_connections: [] },
      related_stories: [],
      provenance: {
        source: "deterministic",
        article_count: 2,
        ai_generated_count: 0,
        deterministic_count: 2,
        is_complete: true,
        completeness_gaps: [],
      },
      quality: {
        overall_quality_score: 0.8,
        quality_flags: ["single_source"],
        quality_explanation: "2 article(s); 1 independent source(s)",
        evidence_coverage: 0.4,
        source_coverage: 0.2,
        conflict_count: 0,
        health_status: "degraded",
        degraded: true,
        degraded_message:
          "Some intelligence for this story is currently unavailable.",
      },
      updated_at: "2026-09-04T00:00:00Z",
      personalization: null,
    }) as unknown as ReturnType<typeof vi.fn>;
    renderWithProviders(<StoryClusterPage />);
    await waitFor(() => {
      expect(screen.getByText("Test Story")).toBeTruthy();
    });
    expect(screen.getByText("Test summary")).toBeTruthy();
    expect(screen.getByText("Takeaway 1")).toBeTruthy();
    expect(screen.getByText("This matters")).toBeTruthy();
    expect(screen.getByText("Tech Daily")).toBeTruthy();
  });

  it("shows degraded quality banner when health is degraded", async () => {
    spy = vi.spyOn(api.publicApi, "storyClusterBrief").mockResolvedValueOnce({
      id: "1",
      title: "Degraded Story",
      slug: "degraded-story",
      status: "ACTIVE",
      article_count: 1,
      source_count: 1,
      independent_source_count: 1,
      summary: null,
      key_takeaways: [],
      why_it_matters: null,
      activity_status: null,
      activity_score: null,
      latest_activity_at: null,
      sources: [],
      claims: [],
      conflicts: [],
      timeline: [],
      story_evolution: null,
      trends: [],
      entities: { companies: [], topics: [], graph_connections: [] },
      related_stories: [],
      provenance: null,
      quality: {
        overall_quality_score: 0.5,
        quality_flags: ["single_source"],
        quality_explanation: "1 article(s); 1 independent source(s)",
        evidence_coverage: 0.2,
        source_coverage: 0.2,
        conflict_count: 0,
        health_status: "degraded",
        degraded: true,
        degraded_message:
          "Some intelligence for this story is currently unavailable.",
      },
      updated_at: "2026-09-04T00:00:00Z",
      personalization: null,
    }) as unknown as ReturnType<typeof vi.fn>;
    renderWithProviders(<StoryClusterPage />);
    await waitFor(() => {
      expect(
        screen.getByText(
          "Some intelligence for this story is currently unavailable.",
        ),
      ).toBeTruthy();
    });
  });

  it("shows provenance badge for AI-derived sources", async () => {
    spy = vi.spyOn(api.publicApi, "storyClusterBrief").mockResolvedValueOnce({
      id: "1",
      title: "AI Story",
      slug: "ai-story",
      status: "ACTIVE",
      article_count: 1,
      source_count: 1,
      independent_source_count: 1,
      summary: null,
      key_takeaways: [],
      why_it_matters: null,
      activity_status: null,
      activity_score: null,
      latest_activity_at: null,
      sources: [
        {
          publisher: "AI Daily",
          source_type: "tech_publication",
          source_role: "Primary",
          article_count: 1,
          provenance_source: "ai_extracted",
          articles: [],
        },
      ],
      claims: [],
      conflicts: [],
      timeline: [],
      story_evolution: null,
      trends: [],
      entities: { companies: [], topics: [], graph_connections: [] },
      related_stories: [],
      provenance: null,
      quality: {
        overall_quality_score: 0.5,
        quality_flags: [],
        quality_explanation: "1 article(s); 1 independent source(s)",
        evidence_coverage: 0.2,
        source_coverage: 0.2,
        conflict_count: 0,
        health_status: "healthy",
        degraded: false,
        degraded_message: null,
      },
      updated_at: "2026-09-04T00:00:00Z",
      personalization: null,
    }) as unknown as ReturnType<typeof vi.fn>;
    renderWithProviders(<StoryClusterPage />);
    await waitFor(() => {
      expect(screen.getByText("AI-derived")).toBeTruthy();
    });
  });
});
