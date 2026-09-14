import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "../../src/auth/AuthContext";
import { Header } from "../../src/components/layout/Header";

function renderHeader() {
  const qc = new QueryClient();
  render(
    <HelmetProvider>
      <QueryClientProvider client={qc}>
        <BrowserRouter>
          <AuthProvider>
            <Header />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe("Header", () => {
  it("renders navigation links", () => {
    renderHeader();
    expect(screen.getByRole("link", { name: /AI News Digest/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /News/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole("link", { name: /Digests/i }).length).toBeGreaterThanOrEqual(1);
  });

  it("renders a skip to content link", () => {
    renderHeader();
    expect(screen.getByText("Skip to content")).toBeInTheDocument();
  });

  it("renders a mobile menu toggle button", () => {
    renderHeader();
    expect(screen.getByRole("button", { name: /toggle navigation menu/i })).toBeInTheDocument();
  });

  it("opens mobile menu when toggle is clicked", () => {
    renderHeader();
    const toggle = screen.getByRole("button", { name: /toggle navigation menu/i });
    fireEvent.click(toggle);
    expect(screen.getByRole("menu")).toBeInTheDocument();
  });

  it("closes mobile menu when escape is pressed", () => {
    renderHeader();
    const toggle = screen.getByRole("button", { name: /toggle navigation menu/i });
    fireEvent.click(toggle);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("has accessible aria-expanded on mobile toggle", () => {
    renderHeader();
    const toggle = screen.getByRole("button", { name: /toggle navigation menu/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });
});
