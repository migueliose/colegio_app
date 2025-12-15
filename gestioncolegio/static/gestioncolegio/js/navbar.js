// Sistema de navbar mejorado para el colegio_app navbar.js
class NavbarManager {
    constructor() {
        this.navbar = document.querySelector('.navbar');
        this.navbarToggler = document.querySelector('.navbar-toggler');
        this.navbarCollapse = document.querySelector('.navbar-collapse');
        this.init();
    }

    init() {
        this.setActiveNavItem();
        this.initScrollEffects();
        this.initMobileBehavior();
        this.initDropdownEnhancements();
        this.initSearchFunctionality();
        this.initNotificationSystem();
    }

    // Activar elemento de navegación actual
    setActiveNavItem() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            const linkPath = link.getAttribute('href');
            
            if (linkPath && currentPath === linkPath) {
                // Coincidencia exacta
                link.classList.add('active');
            } else if (linkPath && linkPath !== '/' && currentPath.startsWith(linkPath)) {
                // Ruta parcial (para subpáginas)
                link.classList.add('active');
            }
        });
        
        // Para la página de inicio
        if (currentPath === '/' || currentPath === '/gestion/') {
            const homeLink = document.querySelector('.navbar-nav .nav-link[href="/"], .navbar-nav .nav-link[href="/gestion/"]');
            if (homeLink) {
                homeLink.classList.add('active');
            }
        }
    }

    // Efectos de scroll
    initScrollEffects() {
        let lastScrollY = window.scrollY;
        const scrollThreshold = 100;

        const handleScroll = () => {
            if (window.scrollY > scrollThreshold) {
                this.navbar.classList.add('navbar-scrolled');
                
                // Ocultar/mostrar navbar al hacer scroll
                if (window.scrollY > lastScrollY && window.scrollY > 200) {
                    this.navbar.style.transform = 'translateY(-100%)';
                } else {
                    this.navbar.style.transform = 'translateY(0)';
                }
            } else {
                this.navbar.classList.remove('navbar-scrolled');
                this.navbar.style.transform = 'translateY(0)';
            }
            
            lastScrollY = window.scrollY;
        };

        // Debounce para mejorar rendimiento
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            if (scrollTimeout) {
                cancelAnimationFrame(scrollTimeout);
            }
            scrollTimeout = requestAnimationFrame(handleScroll);
        });

        // Ejecutar al cargar
        handleScroll();
    }

    // Comportamiento en móviles - CORREGIDO
    initMobileBehavior() {
        if (!this.navbarToggler || !this.navbarCollapse) return;

        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Cerrar navbar al hacer clic en un enlace (solo en móviles)
                if (window.innerWidth < 992 && this.navbarCollapse.classList.contains('show')) {
                    this.navbarToggler.click();
                }
                
                // Smooth scroll solo para enlaces internos válidos
                const href = link.getAttribute('href');
                if (href && href.startsWith('#') && href !== '#') {
                    e.preventDefault();
                    this.smoothScrollTo(href);
                }
            });
        });

        // Mejorar experiencia táctil
        this.navbarCollapse.addEventListener('touchstart', (e) => {
            e.stopPropagation();
        }, { passive: true });
    }

    // Scroll suave - COMPLETAMENTE CORREGIDO
    smoothScrollTo(target) {
        // Validación exhaustiva del target
        if (!target || typeof target !== 'string') {
            console.warn('Target inválido o no proporcionado');
            return;
        }
        
        // Limpiar el target de espacios
        target = target.trim();
        
        // Si el target es solo "#" o comienza con "#" pero no tiene id después
        if (target === '#' || target === '' || target.length <= 1) {
            console.warn('Target de scroll inválido:', target);
            return;
        }
        
        // Verificar que sea un selector CSS válido
        const isValidSelector = (selector) => {
            try {
                document.querySelector(selector);
                return true;
            } catch (error) {
                return false;
            }
        };
        
        if (!isValidSelector(target)) {
            console.warn('Selector CSS inválido:', target);
            return;
        }
        
        // Intentar hacer scroll
        try {
            const targetElement = document.querySelector(target);
            if (targetElement) {
                const headerHeight = this.navbar ? this.navbar.offsetHeight : 0;
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerHeight;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            } else {
                console.warn('Elemento no encontrado para el selector:', target);
            }
        } catch (error) {
            console.error('Error en smoothScrollTo:', error);
        }
    }

    // Mejoras para dropdowns
    initDropdownEnhancements() {
        const dropdowns = document.querySelectorAll('.navbar-nav .dropdown');
        
        dropdowns.forEach(dropdown => {
            const toggle = dropdown.querySelector('.dropdown-toggle');
            const menu = dropdown.querySelector('.dropdown-menu');
            
            if (toggle && menu) {
                // Hover en desktop
                if (window.innerWidth >= 992) {
                    dropdown.addEventListener('mouseenter', () => {
                        const bsDropdown = bootstrap.Dropdown.getInstance(toggle) || new bootstrap.Dropdown(toggle);
                        bsDropdown.show();
                    });
                    
                    dropdown.addEventListener('mouseleave', () => {
                        const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
                        if (bsDropdown) {
                            setTimeout(() => {
                                if (!dropdown.matches(':hover')) {
                                    bsDropdown.hide();
                                }
                            }, 100);
                        }
                    });
                }

                // Mejorar accesibilidad
                toggle.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        const bsDropdown = bootstrap.Dropdown.getInstance(toggle) || new bootstrap.Dropdown(toggle);
                        bsDropdown.toggle();
                    }
                });
            }
        });
    }

    // Sistema de búsqueda (si se implementa)
    initSearchFunctionality() {
        const searchInput = document.querySelector('.navbar-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.handleSearch(e.target.value);
            }, 300));

            searchInput.addEventListener('focus', () => {
                searchInput.parentElement.classList.add('focused');
            });

            searchInput.addEventListener('blur', () => {
                searchInput.parentElement.classList.remove('focused');
            });
        }
    }

    // Manejar búsqueda
    handleSearch(query) {
        if (query.length > 2) {
            console.log('Buscando:', query);
            // Aquí iría la lógica de búsqueda real
        }
    }

    // Sistema de notificaciones
    initNotificationSystem() {
        const notificationBell = document.querySelector('.notification-bell');
        if (notificationBell) {
            notificationBell.addEventListener('click', (e) => {
                e.preventDefault();
                this.showNotifications();
            });
        }
    }

    showNotifications() {
        // Aquí se implementaría el modal de notificaciones
        console.log('Mostrar notificaciones');
    }

    // Utilidad debounce
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Actualizar notificaciones (para usar con WebSockets o polling)
    updateNotificationCount(count) {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            badge.textContent = count;
            if (count > 0) {
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Solo inicializar si existe el navbar
    if (document.querySelector('.navbar')) {
        window.navbarManager = new NavbarManager();
    }
});

// Manejar cambios de tamaño de ventana
window.addEventListener('resize', () => {
    if (window.navbarManager) {
        window.navbarManager.initDropdownEnhancements();
    }
});

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavbarManager;
}