"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, logout, type AuthUser } from "@/controllers/auth-controller";
import { financialDashboard } from "@/models/financial-model";
import { DashboardView } from "@/views/dashboard-view";

export default function GuidePage() {
  const router = useRouter();
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    void getCurrentUser()
      .then((currentUser) => {
        if (!currentUser) {
          router.replace("/");
          return;
        }
        setUser(currentUser);
      })
      .catch(() => router.replace("/"))
      .finally(() => setIsCheckingSession(false));
  }, [router]);

  if (isCheckingSession || !user) return <main className="auth-loading">Comprobando sesión...</main>;

  return (
    <DashboardView
      dashboard={financialDashboard}
      user={user}
      activeSection="Guía de uso"
      onLogout={async () => { await logout(); router.replace("/"); }}
      onEditProfile={() => router.push("/profile")}
      onOpenDashboard={() => router.push("/")}
      onOpenIngestion={() => router.push("/ingestion")}
      onOpenReports={() => router.push("/reports")}
      onOpenGuide={() => router.push("/guide")}
    >
      <section className="user-guide">
        <div className="page-heading">
          <div>
            <p className="eyebrow">PRIMEROS PASOS</p>
            <h1>Guía de uso</h1>
            <p className="heading-copy">Una guía rápida para empezar y una explicación detallada de cada página de la plataforma.</p>
          </div>
        </div>

        <section className="guide-section" aria-labelledby="guide-express-heading">
          <div className="guide-section-heading">
            <p className="eyebrow">PARA EMPEZAR</p>
            <h2 id="guide-express-heading">Guía express</h2>
            <p>El recorrido básico para llegar de tus archivos a la lectura financiera.</p>
          </div>
          <div className="guide-grid">
            <article className="guide-card">
              <h2>1. Carga tus datos</h2>
              <p>En «Carga ERP», elige ERP, banco o presupuesto, selecciona un archivo permitido y pulsa «Subir y guardar».</p>
            </article>
            <article className="guide-card">
              <h2>2. Filtra el resumen</h2>
              <p>En «Resumen», selecciona fechas y área. El horizonte de proyección puede ser de 30, 60 o 90 días.</p>
            </article>
            <article className="guide-card">
              <h2>3. Revisa los resultados</h2>
              <p>Consulta los indicadores, la proyección, las recomendaciones y las alertas. Abre «Evidencia» para ver los datos asociados a una recomendación.</p>
            </article>
            <article className="guide-card">
              <h2>4. Mantén tu cuenta al día</h2>
              <p>Abre el menú de tu avatar para editar tu perfil o cerrar sesión.</p>
            </article>
          </div>
          <div className="guide-start">
            <strong>¿Empiezas desde cero?</strong> Carga datos ERP y presupuestos. Para calcular el flujo bancario y el pronóstico, también necesitas movimientos bancarios. Si aún faltan datos, el resumen puede mostrar indicadores vacíos o una recomendación de datos insuficientes.
          </div>
        </section>

        <section className="guide-section" aria-labelledby="guide-pages-heading">
          <div className="guide-section-heading">
            <p className="eyebrow">REFERENCIA DETALLADA</p>
            <h2 id="guide-pages-heading">Páginas y apartados</h2>
            <p>Qué encontrarás en cada página, qué representa cada dato y cómo interpretarlo.</p>
          </div>

          <article className="guide-page-section">
            <div className="guide-page-heading">
              <span className="guide-page-number">01</span>
              <div>
                <h3>Resumen financiero</h3>
                <p>La vista general de la actividad financiera y de los elementos que requieren atención.</p>
              </div>
            </div>
            <div className="guide-topic-grid">
              <section className="guide-topic">
                <h4>Filtros del periodo</h4>
                <p><strong>Desde / Hasta:</strong> limitan el rango de fechas de los datos del resumen. <strong>Área:</strong> filtra por centro de costo o permite ver todas las áreas. <strong>Forecast:</strong> define cuántos días futuros se proyectan (30, 60 o 90); no es un filtro histórico.</p>
              </section>
              <section className="guide-topic">
                <h4>Última actualización</h4>
                <p>Muestra la fecha y hora de la sincronización financiera más reciente registrada. No significa que los datos se actualicen automáticamente: la carga de archivos es manual.</p>
              </section>
              <section className="guide-topic">
                <h4>Tarjetas de indicadores</h4>
                <ul>
                  <li><strong>Flujo neto bancario:</strong> suma de entradas y salidas bancarias del periodo. No es el saldo de la cuenta.</li>
                  <li><strong>Ingresos del mes:</strong> suma de los ingresos registrados en el periodo.</li>
                  <li><strong>Margen operativo:</strong> proporción de ingresos que queda después de restar gastos operativos: (ingresos − gastos) / ingresos.</li>
                  <li><strong>Desviación presupuestal:</strong> diferencia entre gastos reales y presupuesto, como porcentaje del presupuesto. Un valor positivo indica exceso sobre el presupuesto.</li>
                </ul>
                <p>Solo aparecen los indicadores que se pueden calcular con los datos disponibles. La variación compara con el periodo anterior: «pp» son puntos porcentuales; «%» es un cambio relativo. La flecha indica dirección del cambio, no necesariamente si el resultado es favorable.</p>
              </section>
              <section className="guide-topic">
                <h4>Proyección de flujo neto mensual</h4>
                <ul>
                  <li><strong>Barra sólida:</strong> valor de flujo neto que el modelo proyecta para ese mes. Sobre cero representa flujo neto positivo; debajo de cero, negativo.</li>
                  <li><strong>Franja clara:</strong> intervalo estimado del 80 %, desde el límite inferior hasta el superior. Es un rango posible alrededor de la proyección, no un segundo valor observado.</li>
                  <li><strong>Eje vertical:</strong> importes en MXN. La línea de cero separa valores positivos y negativos.</li>
                  <li><strong>Etiqueta del mes y «d»:</strong> mes pronosticado y cantidad de días de ese mes incluidos en el horizonte seleccionado.</li>
                </ul>
                <p>El flujo neto no equivale al saldo de caja: no incluye por sí solo un saldo inicial.</p>
              </section>
              <section className="guide-topic">
                <h4>Recomendaciones</h4>
                <p>Son avisos generados por reglas financieras a partir de los datos disponibles. La prioridad indica urgencia relativa. Cada tarjeta describe la situación, impacto y acción sugerida. «Evidencia» muestra los identificadores y valores que respaldan la regla. Si no hay datos suficientes, se explica qué fuente o indicador falta.</p>
              </section>
              <section className="guide-topic">
                <h4>Alertas presupuestales</h4>
                <p>Representan desviaciones detectadas frente al presupuesto. El porcentaje indica cuánto se aparta el gasto real del monto presupuestado; la severidad señala el nivel asignado a la alerta. Las alertas cerradas o marcadas como falsas no aparecen en la lista activa.</p>
                <p>Los usuarios con permiso pueden dejar un comentario y cambiar el estado a «En revisión», «Cerrada» o «Falsa». «Gestionar» permite registrar esa atención.</p>
              </section>
              <section className="guide-topic">
                <h4>Otros controles del resumen</h4>
                <p>El menú del avatar permite abrir el perfil o cerrar sesión. «Exportar reporte» guarda una instantánea del resumen actual junto con su PDF en la plataforma.</p>
              </section>
            </div>
          </article>

          <article className="guide-page-section">
            <div className="guide-page-heading">
              <span className="guide-page-number">02</span>
              <div>
                <h3>Reportes</h3>
                <p>Consulta las instantáneas de resumen guardadas en la plataforma.</p>
              </div>
            </div>
            <div className="guide-topic-grid">
              <section className="guide-topic">
                <h4>Exportar y guardar reportes</h4>
                <p>Al pulsar «Exportar reporte» en el resumen se guarda la instantánea y su PDF en la plataforma. Puedes descargar el archivo desde la lista de Reportes. Abrir Reportes solo muestra los reportes guardados y no genera uno automáticamente.</p>
              </section>
              <section className="guide-topic">
                <h4>Buscar y consultar</h4>
                <p>Usa «Fecha del resumen» para filtrar por el último día del periodo resumido. «Ver resumen» muestra los datos guardados y «Descargar PDF» obtiene el archivo almacenado.</p>
              </section>
            </div>
          </article>

          <article className="guide-page-section">
            <div className="guide-page-heading">
              <span className="guide-page-number">03</span>
              <div>
                <h3>Carga ERP</h3>
                <p>Importa manualmente archivos financieros para alimentar los indicadores, alertas y pronósticos.</p>
              </div>
            </div>
            <div className="guide-topic-grid">
              <section className="guide-topic">
                <h4>Fuente de datos</h4>
                <p>Elige <strong>ERP</strong> para movimientos del sistema contable/financiero, <strong>Banco</strong> para transacciones bancarias o <strong>Presupuesto</strong> para los montos planeados que se compararán con el gasto real.</p>
              </section>
              <section className="guide-topic">
                <h4>Archivo financiero</h4>
                <p>ERP y banco admiten PDF, CSV y Excel (.xlsx, .xlsm). Presupuesto admite CSV y Excel con periodo, monto presupuestado, cuenta y centro de costo. El límite es 20 MB. Selecciona el archivo y pulsa «Subir y guardar».</p>
              </section>
              <section className="guide-topic">
                <h4>Resultado de la carga</h4>
                <p>«Guardados» indica cuántos registros se aceptaron; «rechazados» indica cuántos no pudieron procesarse. Los valores originales se conservan en staging para trazabilidad. Si hay un error, revisa el mensaje y valida el formato y los campos requeridos.</p>
              </section>
              <section className="guide-topic">
                <h4>Eliminar datos de práctica</h4>
                <p>Este botón está disponible para CFO, analistas y administradores. Tras confirmar, elimina las cargas cuyo nombre de archivo empieza con «practica_» y los datos derivados de ellas. No es una acción para borrar cualquier archivo importado; revisa bien antes de confirmar.</p>
              </section>
            </div>
          </article>

          <article className="guide-page-section">
            <div className="guide-page-heading">
              <span className="guide-page-number">04</span>
              <div>
                <h3>Perfil</h3>
                <p>Administra los datos personales y las credenciales de la cuenta activa.</p>
              </div>
            </div>
            <div className="guide-topic-grid">
              <section className="guide-topic">
                <h4>Cómo abrirlo</h4>
                <p>Selecciona tu avatar, ubicado en la parte superior derecha, y luego «Editar perfil». Desde esta página también puedes cancelar y volver al resumen.</p>
              </section>
              <section className="guide-topic">
                <h4>Datos personales</h4>
                <p>Puedes actualizar el nombre completo, correo electrónico, nombre de usuario y teléfono. El nombre y el correo son obligatorios; usuario y teléfono son opcionales.</p>
              </section>
              <section className="guide-topic">
                <h4>Contraseña y seguridad</h4>
                <p>Para cambiar el correo o la contraseña, escribe primero la contraseña actual. La nueva contraseña debe tener entre 8 y 128 caracteres. Si solo actualizas el nombre, usuario o teléfono, no necesitas confirmar la contraseña actual.</p>
              </section>
              <section className="guide-topic">
                <h4>Guardar cambios</h4>
                <p>Pulsa «Guardar cambios» para enviar el formulario. La pantalla indicará si se guardó correctamente o si hubo un error. «Cerrar sesión» está en el menú del avatar.</p>
              </section>
            </div>
          </article>
        </section>
      </section>
    </DashboardView>
  );
}
