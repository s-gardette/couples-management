/**
 * Expenses JavaScript functionality
 * Handles expense modals, view switching, and interactions
 */

// Global variables for modal management
let expenseModal = null;

// Initialize expenses page functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeExpenseModal();
    initializeViewSwitching();
    initializeFiltering();
});

/**
 * Initialize the expense modal
 */
function initializeExpenseModal() {
    // Create modal backdrop if it doesn't exist
    if (!document.getElementById('expense-modal-backdrop')) {
        const backdrop = document.createElement('div');
        backdrop.id = 'expense-modal-backdrop';
        backdrop.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 hidden';
        backdrop.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-2xl shadow-lg rounded-md bg-white">
                <div id="expense-modal-content">
                    <!-- Modal content will be loaded here -->
                </div>
            </div>
        `;
        document.body.appendChild(backdrop);
        
        // Close modal when clicking backdrop
        backdrop.addEventListener('click', function(e) {
            if (e.target === backdrop) {
                closeExpenseModal();
            }
        });
    }
}

/**
 * View expense details in a modal
 * @param {string} expenseId - The ID of the expense to view
 */
function viewExpenseDetails(expenseId) {
    const modalContent = document.getElementById('expense-modal-content');
    const backdrop = document.getElementById('expense-modal-backdrop');
    
    if (!modalContent || !backdrop) {
        console.error('Modal elements not found');
        return;
    }
    
    // Show loading state
    modalContent.innerHTML = `
        <div class="text-center py-8">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p class="mt-2 text-gray-600">Loading expense details...</p>
        </div>
    `;
    
    // Show modal
    backdrop.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Fetch expense details
    fetch(`/partials/expenses/${expenseId}/details`)
        .then(response => response.text())
        .then(html => {
            modalContent.innerHTML = html;
        })
        .catch(error => {
            console.error('Error loading expense details:', error);
            modalContent.innerHTML = `
                <div class="bg-white rounded-lg shadow-xl p-6">
                    <div class="text-center">
                        <div class="text-red-500 mb-4">
                            <svg class="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L3.316 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                            </svg>
                        </div>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">Error Loading Expense</h3>
                        <p class="text-gray-600 mb-4">Unable to load expense details. Please try again.</p>
                        <button onclick="closeExpenseModal()" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700">
                            Close
                        </button>
                    </div>
                </div>
            `;
        });
}

/**
 * Close the expense modal
 */
function closeExpenseModal() {
    const backdrop = document.getElementById('expense-modal-backdrop');
    if (backdrop) {
        backdrop.classList.add('hidden');
        document.body.style.overflow = '';
        
        // Clear modal content after animation
        setTimeout(() => {
            const modalContent = document.getElementById('expense-modal-content');
            if (modalContent) {
                modalContent.innerHTML = '';
            }
        }, 200);
    }
}

/**
 * Edit expense (placeholder)
 * @param {string} expenseId - The ID of the expense to edit
 */
function editExpense(expenseId) {
    // TODO: Implement expense editing functionality
    showNotification('Expense editing functionality coming soon!', 'info');
    console.log('Edit expense:', expenseId);
}

/**
 * Delete expense (placeholder)
 * @param {string} expenseId - The ID of the expense to delete
 */
function deleteExpense(expenseId) {
    if (confirm('Are you sure you want to delete this expense? This action cannot be undone.')) {
        // TODO: Implement expense deletion functionality
        showNotification('Expense deletion functionality coming soon!', 'info');
        console.log('Delete expense:', expenseId);
    }
}

/**
 * Duplicate expense (placeholder)
 * @param {string} expenseId - The ID of the expense to duplicate
 */
function duplicateExpense(expenseId) {
    // TODO: Implement expense duplication functionality
    showNotification('Expense duplication functionality coming soon!', 'info');
    console.log('Duplicate expense:', expenseId);
}

/**
 * Show notification to user
 * @param {string} message - The message to show
 * @param {string} type - The type of notification (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification-toast');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-toast fixed top-4 right-4 z-50 max-w-sm w-full bg-white border-l-4 p-4 shadow-lg rounded-md transition-all duration-300 transform translate-x-full`;
    
    // Set border color based on type
    const typeColors = {
        success: 'border-green-500',
        error: 'border-red-500',
        warning: 'border-yellow-500',
        info: 'border-blue-500'
    };
    
    const iconColors = {
        success: 'text-green-500',
        error: 'text-red-500',
        warning: 'text-yellow-500',
        info: 'text-blue-500'
    };
    
    const icons = {
        success: 'M5 13l4 4L19 7',
        error: 'M6 18L18 6M6 6l12 12',
        warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L3.316 16.5c-.77.833.192 2.5 1.732 2.5z',
        info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
    };
    
    notification.classList.add(typeColors[type] || typeColors.info);
    
    notification.innerHTML = `
        <div class="flex items-start">
            <div class="flex-shrink-0">
                <svg class="h-5 w-5 ${iconColors[type] || iconColors.info}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${icons[type] || icons.info}"></path>
                </svg>
            </div>
            <div class="ml-3 flex-1">
                <p class="text-sm font-medium text-gray-900">${message}</p>
            </div>
            <div class="ml-4 flex-shrink-0">
                <button onclick="this.parentElement.parentElement.parentElement.remove()" class="text-gray-400 hover:text-gray-600 focus:outline-none">
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 5000);
}

/**
 * Initialize view switching functionality
 */
function initializeViewSwitching() {
    const viewButtons = document.querySelectorAll('[data-view-mode]');
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const viewMode = this.getAttribute('data-view-mode');
            switchView(viewMode);
        });
    });
}

/**
 * Switch between card and table view
 * @param {string} viewMode - 'cards' or 'table'
 */
function switchView(viewMode) {
    // Update button states
    const viewButtons = document.querySelectorAll('[data-view-mode]');
    viewButtons.forEach(button => {
        if (button.getAttribute('data-view-mode') === viewMode) {
            button.classList.add('bg-indigo-100', 'text-indigo-700');
            button.classList.remove('text-gray-500', 'hover:text-gray-700');
        } else {
            button.classList.remove('bg-indigo-100', 'text-indigo-700');
            button.classList.add('text-gray-500', 'hover:text-gray-700');
        }
    });
    
    // Trigger HTMX update with new view mode
    applyFilters(viewMode);
}

/**
 * Initialize filtering functionality
 */
function initializeFiltering() {
    const filterInputs = document.querySelectorAll('#expenses-filters input, #expenses-filters select');
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            applyFilters();
        });
    });
    
    // Add search input debouncing
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                applyFilters();
            }, 500); // 500ms debounce
        });
    }
}

/**
 * Apply current filters and trigger HTMX update
 * @param {string} overrideViewMode - Optional view mode to override current selection
 */
function applyFilters(overrideViewMode = null) {
    const filtersForm = document.getElementById('expenses-filters');
    const expensesContainer = document.getElementById('expenses-container');
    
    if (!filtersForm || !expensesContainer) {
        console.error('Required filter elements not found');
        return;
    }
    
    // Get current view mode
    let viewMode = overrideViewMode;
    if (!viewMode) {
        const activeViewButton = document.querySelector('[data-view-mode].bg-indigo-100');
        viewMode = activeViewButton ? activeViewButton.getAttribute('data-view-mode') : 'cards';
    }
    
    // Build query parameters
    const formData = new FormData(filtersForm);
    const params = new URLSearchParams(formData);
    params.set('view_mode', viewMode);
    params.set('view_type', 'list'); // Always use list view type for filtering
    
    // Get household ID from the page
    const householdId = expensesContainer.getAttribute('data-household-id');
    if (householdId) {
        params.set('household_id', householdId);
    }
    
    // Show loading state
    expensesContainer.innerHTML = `
        <div class="text-center py-8">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p class="mt-2 text-gray-600">Loading expenses...</p>
        </div>
    `;
    
    // Fetch updated expenses
    const url = `/partials/expenses/recent?${params.toString()}`;
    fetch(url)
        .then(response => response.text())
        .then(html => {
            expensesContainer.innerHTML = html;
        })
        .catch(error => {
            console.error('Error applying filters:', error);
            expensesContainer.innerHTML = `
                <div class="text-center py-8">
                    <div class="text-red-500 mb-4">
                        <svg class="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L3.316 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                        </svg>
                    </div>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">Error Loading Expenses</h3>
                    <p class="text-gray-600 mb-4">Unable to load expenses. Please try again.</p>
                    <button onclick="applyFilters()" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                        Retry
                    </button>
                </div>
            `;
        });
}

/**
 * Reset all filters
 */
function resetFilters() {
    const filtersForm = document.getElementById('expenses-filters');
    if (filtersForm) {
        filtersForm.reset();
        applyFilters();
    }
}

/**
 * Handle keyboard shortcuts
 */
document.addEventListener('keydown', function(e) {
    // Close modal with Escape key
    if (e.key === 'Escape') {
        closeExpenseModal();
    }
});

// Export functions for use in templates
window.viewExpenseDetails = viewExpenseDetails;
window.editExpense = editExpense;
window.deleteExpense = deleteExpense;
window.duplicateExpense = duplicateExpense;
window.closeExpenseModal = closeExpenseModal;
window.showNotification = showNotification;
window.switchView = switchView;
window.applyFilters = applyFilters;
window.resetFilters = resetFilters; 