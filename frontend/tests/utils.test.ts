import { describe, it, expect } from "vitest";
import { formatDate, truncate, cn, safeRedirect } from "../src/utils";

describe("formatDate", () => {
  it("formats an ISO date", () => {
    const result = formatDate("2026-08-23T12:00:00Z");
    expect(result).toContain("2026");
    expect(result).toContain("Aug");
  });

  it("returns a dash for null/undefined", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
  });
});

describe("truncate", () => {
  it("leaves short strings untouched", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });

  it("truncates long strings with an ellipsis", () => {
    const long = "a".repeat(300);
    expect(truncate(long, 180)).toHaveLength(181);
    expect(truncate(long, 180).endsWith("…")).toBe(true);
  });
});

describe("cn", () => {
  it("joins class names and drops falsy values", () => {
    expect(cn("a", "b", false, null, undefined, "c")).toBe("a b c");
  });
});

describe("safeRedirect", () => {
  it("returns relative paths starting with single slash", () => {
    expect(safeRedirect("/me")).toBe("/me");
    expect(safeRedirect("/dashboard")).toBe("/dashboard");
    expect(safeRedirect("/articles/123")).toBe("/articles/123");
  });

  it("falls back for null and empty", () => {
    expect(safeRedirect(null)).toBe("/me");
    expect(safeRedirect("")).toBe("/me");
    expect(safeRedirect("   ")).toBe("/me");
  });

  it("blocks protocol-relative URLs (double slash)", () => {
    expect(safeRedirect("//evil.com")).toBe("/me");
    expect(safeRedirect("//evil.com/steal")).toBe("/me");
  });

  it("blocks absolute URLs with scheme", () => {
    expect(safeRedirect("https://evil.com")).toBe("/me");
    expect(safeRedirect("http://evil.com")).toBe("/me");
  });

  it("blocks backslash-based redirects", () => {
    expect(safeRedirect("\\evil.com")).toBe("/me");
    expect(safeRedirect("\\\\evil.com")).toBe("/me");
  });

  it("blocks backslashes inside otherwise relative paths", () => {
    expect(safeRedirect("/login\\evil.com")).toBe("/me");
  });

  it("uses the provided fallback", () => {
    expect(safeRedirect(null, "/dashboard")).toBe("/dashboard");
    expect(safeRedirect("https://evil.com", "/dashboard")).toBe("/dashboard");
  });
});
