"use client";

import { FormEvent, useState } from "react";
import { updateProfile, type AuthUser } from "@/controllers/auth-controller";

type ProfileViewProps = { user: AuthUser; onCancel: () => void; onSaved: (user: AuthUser) => void };

export function ProfileView({ user, onCancel, onSaved }: ProfileViewProps) {
  const [email, setEmail] = useState(user.email);
  const [newPassword, setNewPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const requiresReauthentication = email.trim().toLowerCase() !== user.email.toLowerCase() || newPassword.length > 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");
    setIsSubmitting(true);
    const form = event.currentTarget;
    const data = new FormData(form);

    try {
      const updatedUser = await updateProfile({
        email: email.trim(),
        full_name: String(data.get("fullName") ?? "").trim(),
        username: String(data.get("username") ?? "").trim() || undefined,
        phone: String(data.get("phone") ?? "").trim() || undefined,
        current_password: String(data.get("currentPassword") ?? "") || undefined,
        new_password: newPassword || undefined,
      });
      onSaved(updatedUser);
      setEmail(updatedUser.email);
      setNewPassword("");
      form.reset();
      setSuccessMessage("Los cambios se guardaron correctamente.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "No se pudieron guardar los cambios.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="profile-page">
      <div className="profile-page-header">
        <div>
          <p className="eyebrow">CUENTA Y SEGURIDAD</p>
          <h1>Editar perfil</h1>
          <p className="heading-copy">Actualiza tus datos personales y credenciales de acceso.</p>
        </div>
        <button type="button" className="secondary-button" onClick={onCancel}>Cancelar</button>
      </div>

      {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}
      {successMessage && (
        <div className="profile-success" role="status">
          {successMessage} <button type="button" className="profile-back-link" onClick={onCancel}>Volver al resumen</button>
        </div>
      )}

      <form
        key={`${user.id}:${user.email}:${user.full_name}:${user.username ?? ""}:${user.phone ?? ""}`}
        className="profile-form"
        onSubmit={handleSubmit}
      >
        <label>
          <span>Nombre completo *</span>
          <input name="fullName" defaultValue={user.full_name} autoComplete="name" required minLength={2} maxLength={255} />
        </label>
        <label>
          <span>Correo electrónico *</span>
          <input name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required minLength={5} maxLength={255} />
        </label>
        <label>
          <span>Nombre de usuario</span>
          <input name="username" defaultValue={user.username ?? ""} autoComplete="username" pattern="[a-zA-Z0-9_.-]+" minLength={3} maxLength={50} />
        </label>
        <label>
          <span>Teléfono</span>
          <input name="phone" defaultValue={user.phone ?? ""} autoComplete="tel" inputMode="tel" pattern="\+?[0-9 ()-]{7,20}" minLength={7} maxLength={20} />
        </label>

        <section className="profile-sensitive-section" aria-labelledby="profile-security-heading">
          <p className="eyebrow" id="profile-security-heading">CAMBIOS SENSIBLES</p>
          <p className="profile-help">Para cambiar el correo o la contraseña, confirma tu contraseña actual.</p>
          <label>
            <span>Contraseña actual{requiresReauthentication ? " *" : ""}</span>
            <input name="currentPassword" type="password" autoComplete="current-password" minLength={8} maxLength={128} required={requiresReauthentication} />
          </label>
          <label>
            <span>Nueva contraseña</span>
            <input name="newPassword" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} maxLength={128} />
          </label>
        </section>

        <div className="profile-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>Cancelar</button>
          <button type="submit" className="primary-button" disabled={isSubmitting}>{isSubmitting ? "Guardando..." : "Guardar cambios"}</button>
        </div>
      </form>
    </main>
  );
}