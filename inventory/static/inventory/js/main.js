document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const sidebarToggle = document.getElementById('sidebar-toggle');

    // Sidebar toggle for mobile view
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('sidebar-closed');
            mainContent.classList.toggle('main-content-expanded');
        });
    }

    // --- THIS IS THE FIX FOR THE EXPANDABLE MENUS ---
    // Find all submenu toggles and add a click event listener
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    submenuToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            // Get the next element, which is the submenu ul
            const submenu = this.nextElementSibling;
            // Get the arrow icon
            const arrowIcon = this.querySelector('i.fa-chevron-down');

            // Toggle the 'hidden' class to show/hide the menu
            submenu.classList.toggle('hidden');
            
            // Rotate the arrow icon
            if (arrowIcon) {
                arrowIcon.classList.toggle('rotate-180');
            }
        });
    });
});