import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { StoryCard } from "../../src/components/StoryCard";

describe("StoryCard", () => {
  it("does not render a story link when the story has no slug", () => {
    render(
      <BrowserRouter>
        <StoryCard
          story={{
            cluster_id: "cluster-123",
            slug: null,
            headline: "Headline without slug",
            summary: "Summary text",
            key_takeaways: ["Takeaway one"],
          }}
          index={0}
        />
      </BrowserRouter>,
    );

    expect(screen.getByText("Headline without slug")).toBeInTheDocument();
    expect(screen.getByText("Summary text")).toBeInTheDocument();
    expect(screen.queryByText("View full story")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "View full story" })).not.toBeInTheDocument();
  });

  it("renders a story link when the story has a valid slug", () => {
    render(
      <BrowserRouter>
        <StoryCard
          story={{
            cluster_id: "cluster-123",
            slug: "valid-story-slug",
            headline: "Headline with slug",
            summary: "Summary text",
            key_takeaways: ["Takeaway one"],
          }}
          index={1}
        />
      </BrowserRouter>,
    );

    const link = screen.getByRole("link", { name: "View full story" });
    expect(link).toHaveAttribute("href", "/stories/valid-story-slug");
  });
});
