/*****************************
 *  SISTEMA DE TEMAS (LIGHT / DARK)
 *****************************/

// Guarda y aplica un tema
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    // Actualizar icono del toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');
        if (icon) {
            icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
}

// Detectar preferencia del sistema
function detectSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

// Inicializar tema correctamente
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemTheme = detectSystemTheme();
    const theme = savedTheme || systemTheme;

    setTheme(theme);

    // Cambios del sistema
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
}

/*****************************
 *  CAROUSEL LAZY LOADING
 *****************************/
function initCarousels() {
    const carousels = document.querySelectorAll('.carousel');

    carousels.forEach(carousel => {
        if (carousel && !carousel._carouselInstance) {

            // Lazy loading
            const images = carousel.querySelectorAll('img[data-src]');
            images.forEach(img => {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
            });

            try {
                const instance = new bootstrap.Carousel(carousel, {
                    interval: CONFIG?.carouselInterval || 5000,
                    pause: 'hover',
                    wrap: true,
                    touch: true,
                    keyboard: true
                });

                carousel._carouselInstance = instance;

                // Pausar cuando no está visible
                const observer = new IntersectionObserver(entries => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            instance.cycle();
                        } else {
                            instance.pause();
                        }
                    });
                }, { threshold: 0.5 });

                observer.observe(carousel);
            } catch (err) {
                console.error("Error inicializando carrusel:", err.message);
            }
        }
    });
}

/*****************************
 *  EVENTO PRINCIPAL
 *****************************/
document.addEventListener('DOMContentLoaded', () => {

    // Inicializar tema
    initTheme();

    // Toggle del tema
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            setTheme(current === 'dark' ? 'light' : 'dark');
        });
    }

    // Inicializar carruseles
    initCarousels();
});
