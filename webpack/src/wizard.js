import Alpine from 'alpinejs';
import htmx from 'htmx.org';

window.Alpine = Alpine;
window.htmx = htmx;

document.addEventListener('DOMContentLoaded', () => Alpine.start());
