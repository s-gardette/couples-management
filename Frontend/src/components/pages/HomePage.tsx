import React from 'react';
import { Button } from '@/components/ui/button';
import FeatureCard from '../common/FeatureCard';
import PageContainer from '../layout/PageContainer';

export default function HomePage() {
  return (
    <PageContainer>
      <div className="text-center space-y-8">
        {/* Hero Section */}
        <div className="space-y-4">
          <h1 className="text-4xl font-bold tracking-tight">
            Manage Your Relationship Finances Together
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Track expenses, manage budgets, and coordinate financial decisions with your partner in one simple app.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex justify-center gap-4 flex-wrap">
          <Button size="lg" asChild>
            <a href="/auth/signup">Get Started</a>
          </Button>
          <Button variant="outline" size="lg" asChild>
            <a href="/dashboard">View Dashboard</a>
          </Button>
          <Button variant="ghost" size="lg" asChild>
            <a href="/auth/signin">Sign In</a>
          </Button>
        </div>

        {/* Features Section */}
        <div className="grid md:grid-cols-3 gap-8 mt-16">
          <FeatureCard
            title="Track Expenses"
            description="Easily log and categorize household expenses with our intuitive interface."
            icon={
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            }
          />
          
          <FeatureCard
            title="Manage Budgets"
            description="Set and monitor budgets for different categories to stay on track with your financial goals."
            icon={
              <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            }
          />
          
          <FeatureCard
            title="Coordinate Payments"
            description="Track who owes what and settle payments between household members effortlessly."
            icon={
              <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            }
          />
        </div>

        {/* Additional Features */}
        <div className="mt-16 p-8 bg-muted/50 rounded-lg">
          <h2 className="text-2xl font-semibold mb-4">Why Choose Couples Management?</h2>
          <div className="grid md:grid-cols-2 gap-6 text-left">
            <div className="space-y-2">
              <h3 className="font-medium">🔒 Secure & Private</h3>
              <p className="text-sm text-muted-foreground">Your financial data is encrypted and secure with modern authentication.</p>
            </div>
            <div className="space-y-2">
              <h3 className="font-medium">📱 Mobile Friendly</h3>
              <p className="text-sm text-muted-foreground">Access your finances on any device with our responsive design.</p>
            </div>
            <div className="space-y-2">
              <h3 className="font-medium">⚡ Real-time Sync</h3>
              <p className="text-sm text-muted-foreground">Changes sync instantly between you and your partner.</p>
            </div>
            <div className="space-y-2">
              <h3 className="font-medium">📊 Smart Insights</h3>
              <p className="text-sm text-muted-foreground">Get insights into your spending patterns and habits.</p>
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  );
} 