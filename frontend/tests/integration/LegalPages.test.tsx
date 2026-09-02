import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
import { PrivacyPolicyPage } from "../../src/pages/public/PrivacyPolicyPage";
import { TermsOfServicePage } from "../../src/pages/public/TermsOfServicePage";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );
}

describe("PrivacyPolicyPage", () => {
  it("renders the privacy policy heading", () => {
    renderWithProviders(<PrivacyPolicyPage />);
    expect(screen.getByText("Privacy Policy")).toBeInTheDocument();
  });

  it("renders data retention section", () => {
    renderWithProviders(<PrivacyPolicyPage />);
    expect(screen.getByText("4. Data Retention")).toBeInTheDocument();
  });

  it("renders account deletion section", () => {
    renderWithProviders(<PrivacyPolicyPage />);
    expect(screen.getByText("5. Account Deletion")).toBeInTheDocument();
  });
});

describe("TermsOfServicePage", () => {
  it("renders the terms of service heading", () => {
    renderWithProviders(<TermsOfServicePage />);
    expect(screen.getByText("Terms of Service")).toBeInTheDocument();
  });

  it("renders acceptable use section", () => {
    renderWithProviders(<TermsOfServicePage />);
    expect(screen.getByText("4. Acceptable Use")).toBeInTheDocument();
  });

  it("renders limitation of liability section", () => {
    renderWithProviders(<TermsOfServicePage />);
    expect(screen.getByText("8. Limitation of Liability")).toBeInTheDocument();
  });
});
