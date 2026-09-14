import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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
  ],
  total: 1,
  limit: 12,
  offset: 0,
};

const CATEGORIES = [
  { id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", name: "Technology", description: "Tech" },
];

const server = setupServer(
  http.get("/api/v1/public/articles", () => HttpResponse.json(ARTICLES)),
  http.get("/api/v1/public/categories", () => HttpResponse.json(CATEGORIES)),
  http.get("/api/v1/public/sources", () => HttpResponse.json([])),
  http.get("/api/v1/public/companies", () => HttpResponse.json([])),
  http.get("/api/v1/public/topics", () => HttpResponse.json([])),
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

describe("NewsPage filter UX", () => {
  it("renders a filter toggle button", async () => {
    renderPage();
    expect(screen.getByRole("button", { name: /hide filters/i })).toBeInTheDocument();
  });

  it("hides filters when toggle is clicked", async () => {
    renderPage();
    const toggle = screen.getByRole("button", { name: /hide filters/i });
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(screen.queryByText("Category")).not.toBeInTheDocument();
    });
  });

  it("shows filters when toggle is clicked again", async () => {
    renderPage();
    const toggle = screen.getByRole("button", { name: /hide filters/i });
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(screen.queryByText("Category")).not.toBeInTheDocument();
    });
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(screen.getByText("Category")).toBeInTheDocument();
    });
  });

  it("shows active filter indicator when filters are active", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Technology" })).toBeInTheDocument();
    });
    const categoryButton = screen.getByRole("button", { name: "Technology" });
    fireEvent.click(categoryButton);
    expect(screen.getByText("Active filters:")).toBeInTheDocument();
  });
});
