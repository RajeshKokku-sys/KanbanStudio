import { render, screen, fireEvent } from "@testing-library/react";
import LoginPage from "./page";

// Mock next/navigation useRouter
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    // Clear sessionStorage and mock calls before each test
    sessionStorage.clear();
    mockReplace.mockReset();
  });

  it("redirects to home on successful login", async () => {
    render(<LoginPage />);

    const usernameInput = screen.getByTestId("username-input");
    const passwordInput = screen.getByTestId("password-input");
    const button = screen.getByTestId("login-button");

    fireEvent.change(usernameInput, { target: { value: "user" } });
    fireEvent.change(passwordInput, { target: { value: "password" } });
    fireEvent.click(button);

    // Expect sessionStorage flag set and navigation to home
    expect(sessionStorage.getItem("auth")).toBe("true");
    expect(mockReplace).toHaveBeenCalledWith("/");
  });

  it("shows error on invalid credentials", () => {
    render(<LoginPage />);
    const usernameInput = screen.getByTestId("username-input");
    const passwordInput = screen.getByTestId("password-input");
    const button = screen.getByTestId("login-button");

    fireEvent.change(usernameInput, { target: { value: "bad" } });
    fireEvent.change(passwordInput, { target: { value: "creds" } });
    fireEvent.click(button);

    expect(screen.getByTestId("error-msg")).toHaveTextContent("Invalid credentials");
    expect(sessionStorage.getItem("auth")).toBeNull();
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
