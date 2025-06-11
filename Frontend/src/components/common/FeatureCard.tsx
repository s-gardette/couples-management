import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface FeatureCardProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  href?: string;
  buttonText?: string;
  variant?: 'default' | 'interactive';
}

export default function FeatureCard({ 
  title, 
  description, 
  icon, 
  href, 
  buttonText,
  variant = 'default' 
}: FeatureCardProps) {
  const cardClassName = variant === 'interactive' 
    ? "hover:shadow-lg transition-shadow cursor-pointer" 
    : "";

  const content = (
    <Card className={cardClassName}>
      <CardHeader>
        <CardTitle className="flex items-center">
          {icon && <span className="mr-2">{icon}</span>}
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {(href || buttonText) && (
        <CardContent>
          {href && buttonText ? (
            <Button variant="outline" size="sm" className="w-full" asChild>
              <a href={href}>{buttonText}</a>
            </Button>
          ) : null}
        </CardContent>
      )}
    </Card>
  );

  if (href && !buttonText) {
    return (
      <a href={href} className="block">
        {content}
      </a>
    );
  }

  return content;
} 