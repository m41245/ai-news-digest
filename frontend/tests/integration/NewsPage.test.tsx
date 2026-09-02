import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { NewsPage } from "../../src/pages/public/NewsPage";

const ARTICLES = {
  items: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      title: "First article",
      url: "https://example.com/1",
      summary: "Summary one",
      status: "ready",
      published_at: "2026-08-23T12:00:00Z",
      source_name: "Test Source",
      category_name: "Technology",
    },
    {
      id: "22222222-2222-2222-2222-222222222222",
      title: "Second article",
      url: "https://example.com/2",
      summary: "Summary two",
      status: "summarized",
      published_at: "2026-08-22T12:00:00Z",
      source_name: "Test Source",
      category_name: null,
    },
  ],
  total: 2,
  limit: 12,
  offset: 0,
};

const CATEGORIES = [
  { id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", name: "Technology", description: "Tech" },
];

const server = setupServer(
  http.get("/api/v1/public/articles", () => HttpResponse.json(ARTICLES)),
  http.get("/api/v1/public/categories", () => HttpResponse.json(CATEGORIES)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
beforeEach(() => server.resetHandlers());

function renderPage() {
  const qc = new QueryClient();
  render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <BrowserRouter>
          <NewsPage />
        </BrowserRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe("NewsPage integration", () => {
  it("loads and renders articles from the API", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("First article")).toBeInTheDocument();
      expect(screen.getByText("Second article")).toBeInTheDocument();
    });

    expect(screen.getByText("2 articles")).toBeInTheDocument();
  });

  it("has an accessible search form", async () => {
    renderPage();

    expect(screen.getByRole("search")).toBeInTheDocument();
    expect(screen.getByLabelText("Search articles")).toBeInTheDocument();
  });

  it("renders category filters once loaded", async () => {
    renderPage();

    await waitFor(() => {
      const buttons = screen.getAllByRole("button", { name: "Technology" });
      expect(buttons.length).toBeGreaterThanOrEqual(1);
    });
  });
});
