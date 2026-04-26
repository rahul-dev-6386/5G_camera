import { z } from "zod";

export const loginSchema = z.object({
  username: z
    .string()
    .min(1, "Username is required")
    .min(3, "Username must be at least 3 characters")
    .max(32, "Username must be at most 32 characters"),
  password: z
    .string()
    .min(1, "Password is required")
    .min(8, "Password must be at least 8 characters"),
});

export const signupSchema = z.object({
  full_name: z
    .string()
    .min(1, "Full name is required")
    .min(5, "Full name must be at least 5 characters"),
  username: z
    .string()
    .min(1, "Username is required")
    .min(3, "Username must be at least 3 characters")
    .max(32, "Username must be at most 32 characters"),
  password: z
    .string()
    .min(1, "Password is required")
    .min(8, "Password must be at least 8 characters")
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      "Password must contain uppercase, lowercase, and digit"
    ),
});

export function validateAuthForm(authMode, formData) {
  const schema = authMode === "login" ? loginSchema : signupSchema;
  const result = schema.safeParse(formData);

  if (!result.success) {
    const errors = {};
    result.error.issues.forEach((issue) => {
      const key = issue.path[0];
      if (!errors[key]) {
        errors[key] = issue.message;
      }
    });
    return { valid: false, errors };
  }

  return { valid: true, errors: {} };
}
