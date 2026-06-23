import Alpine from 'alpinejs';
import htmx from 'htmx.org';
import './css/wizard.scss';

window.Alpine = Alpine;
window.htmx = htmx;

document.addEventListener('DOMContentLoaded', () => Alpine.start());
