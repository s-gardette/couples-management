import React from 'react';

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'centered' | 'full-width';
}

export default function PageContainer({ 
  children, 
  className = '', 
  variant = 'default' 
}: PageContainerProps) {
  const getContainerClasses = () => {
    switch (variant) {
      case 'centered':
        return 'flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8';
      case 'full-width':
        return 'w-full';
      default:
        return 'max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 px-4';
    }
  };

  return (
    <div className={`${getContainerClasses()} ${className}`}>
      {children}
    </div>
  );
} 