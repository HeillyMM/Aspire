/* =========================
   Script Profesional OportuniLink
========================= */

/* Flash Messages Animadas */
document.addEventListener("DOMContentLoaded", () => {
    const flashMessages = document.querySelectorAll(".flash-message");

    flashMessages.forEach(msg => {
        // Aparece con fade
        msg.classList.add("show");
        // Desaparece automáticamente después de 4 segundos
        setTimeout(() => {
            msg.classList.remove("show");
            msg.style.display = "none";
        }, 4000);
    });
});

/* Animación de botones y microinteracciones */
const buttons = document.querySelectorAll(".btn-primary, .btn-secondary, .btn-profile");

buttons.forEach(button => {
    button.addEventListener("mouseenter", () => {
        button.style.transform = "translateY(-3px)";
        button.style.boxShadow = "0 8px 20px rgba(0,0,0,0.2)";
    });
    button.addEventListener("mouseleave", () => {
        button.style.transform = "translateY(0)";
        button.style.boxShadow = "none";
    });
});

/* Smooth Scroll para navegación de anclas */
const links = document.querySelectorAll('a[href^="#"]');
links.forEach(link => {
    link.addEventListener("click", function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute("href"));
        if (target) {
            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }
    });
});

/* Input focus efecto */
const inputs = document.querySelectorAll("input, textarea");
inputs.forEach(input => {
    input.addEventListener("focus", () => {
        input.style.borderColor = "#0077b5";
        input.style.boxShadow = "0 0 8px rgba(0,119,181,0.3)";
    });
    input.addEventListener("blur", () => {
        input.style.borderColor = "#ccc";
        input.style.boxShadow = "none";
    });
});

/* Perfil Card hover efecto */
const profileCards = document.querySelectorAll(".profile-card");
profileCards.forEach(card => {
    card.addEventListener("mouseenter", () => {
        card.style.transform = "translateY(-5px)";
        card.style.boxShadow = "0 12px 30px rgba(0,0,0,0.2)";
    });
    card.addEventListener("mouseleave", () => {
        card.style.transform = "translateY(0)";
        card.style.boxShadow = "0 8px 20px rgba(0,0,0,0.1)";
    });
});

function togglePerfilPanel() {
    const panel = document.getElementById('perfilPanel');
    panel.classList.toggle('open');
}

// Perfil flotante
function togglePerfilPanel() {
    const panel = document.getElementById('perfilPanel');
    panel.classList.toggle('open');
}

// Tabs feed
function switchTab(tabName, event) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.feed-tabs button').forEach(b => b.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    if(event) event.currentTarget.classList.add('active');
}

// Para que se vea por defecto la primera tab
document.addEventListener('DOMContentLoaded', () => {
    const firstTab = document.querySelector('.feed-tabs button');
    if(firstTab) firstTab.click();
});

// abrir/cerrar panel perfil (si lo usas)
function togglePerfilPanel() {
  const panel = document.getElementById('perfilPanel');
  if (!panel) return;
  panel.classList.toggle('open');
}

// tabs del feed
function switchTab(tabName, event) {
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.feed-tabs .tab, .feed-tabs button').forEach(b => b.classList.remove('active'));
  const el = document.getElementById(tabName);
  if (el) el.classList.add('active');
  if (event && event.currentTarget) event.currentTarget.classList.add('active');
}

document.addEventListener('DOMContentLoaded', () => {
  // click inicial en primera tab (si no hay click)
  const first = document.querySelector('.feed-tabs .tab, .feed-tabs button');
  if (first) first.click();
});