import React from 'react';
import { Button } from '@/components/ui/button';

interface NavigationItem {
  key: string;
  label: string;
  href: string;
  variant?: 'ghost' | 'outline' | 'default';
  size?: 'sm' | 'lg';
}

interface NavigationProps {
  variant?: 'default' | 'auth' | 'dashboard';
}

export default function Navigation({ variant = 'default' }: NavigationProps) {
  // Base navigation items that are common across variants
  const baseNavItems: NavigationItem[] = [
    {
      key: 'dashboard',
      label: 'Dashboard',
      href: '/dashboard',
      variant: 'ghost',
      size: 'sm'
    },
    {
      key: 'signin',
      label: 'Sign In',
      href: '/auth/signin',
      variant: 'outline',
      size: 'sm'
    },
    {
      key: 'signup',
      label: 'Get Started',
      href: '/auth/signup',
      variant: 'default',
      size: 'sm'
    }
  ];

  // Variant-specific modifications
  const getNavigationItems = (): NavigationItem[] => {
    let items = [...baseNavItems]; // Start with base items
    
    switch (variant) {
      case 'auth':
        // For auth pages, replace all items with just back to home
        return [
          {
            key: 'back-home',
            label: '← Back to Home',
            href: '/',
            variant: 'ghost',
            size: 'sm'
          }
        ];
      
      case 'dashboard':
        // For dashboard, remove signin/signup and add dashboard-specific items
        items = items.filter(item => !['signin', 'signup'].includes(item.key));
        items.unshift({
          key: 'profile',
          label: 'Profile',
          href: '/profile',
          variant: 'ghost',
          size: 'sm'
        });
        items.push(
          {
            key: 'settings',
            label: 'Settings',
            href: '/settings',
            variant: 'ghost',
            size: 'sm'
          },
          {
            key: 'logout',
            label: 'Logout',
            href: '/auth/logout',
            variant: 'outline',
            size: 'sm'
          }
        );
        return items;
      
      default:
        // Default variant uses base items as-is
        return items;
    }
  };

  const navigationItems = getNavigationItems();

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Button variant="ghost" size="lg" asChild>
              <a href="/" className="text-xl font-semibold">
                Couples Management
              </a>
            </Button>
          </div>
          
          <div className="flex items-center space-x-4">
            {navigationItems.map((item) => (
              <Button
                key={item.key}
                variant={item.variant || 'ghost'}
                size={item.size || 'sm'}
                asChild
              >
                <a href={item.href}>{item.label}</a>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
} 