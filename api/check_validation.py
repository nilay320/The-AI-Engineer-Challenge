#!/usr/bin/env python3
"""
Show the validation criteria used by the RAG system.
"""

def show_validation_criteria():
    """Display the keywords and criteria used for content validation."""
    
    print("🎯 RAG System Content Validation Criteria")
    print("=" * 60)
    
    print("📋 ACCEPTANCE THRESHOLD: Final score ≥ 4.0/10")
    print("📊 SCORING FORMULA: (keyword_density × 2 + ai_score) ÷ 3")
    print("")
    
    print("🔍 REQUIRED KEYWORDS (searches for these terms):")
    
    startup_keywords = [
        # Core startup terms
        'startup', 'business', 'company', 'entrepreneur', 'venture', 'funding', 'investment',
        'revenue', 'profit', 'market', 'customer', 'product', 'service', 'strategy',
        'business plan', 'pitch', 'investor', 'valuation', 'growth', 'scale', 'competition',
        'team', 'founder', 'CEO', 'CTO', 'board', 'equity', 'shares', 'financial',
        'marketing', 'sales', 'operations', 'model', 'vision', 'mission', 'goals',
        'metrics', 'KPI', 'ROI', 'CAC', 'LTV', 'churn', 'acquisition', 'retention',
        'ecosystem', 'industry', 'sector', 'corporate', 'organization', 'management',
        
        # Startup methodologies and frameworks
        'lean startup', 'agile', 'mvp', 'minimum viable product', 'product market fit',
        'pivot', 'iteration', 'hypothesis', 'validation', 'feedback loop', 'user research',
        'design thinking', 'customer development', 'build measure learn', 'sprint',
        'scrum', 'kanban', 'roadmap', 'backlog', 'user story', 'persona', 'journey',
        
        # Business best practices and concepts
        'best practices', 'framework', 'methodology', 'process', 'workflow', 'optimization',
        'efficiency', 'productivity', 'performance', 'quality', 'standards', 'guidelines',
        'governance', 'compliance', 'risk management', 'decision making', 'leadership',
        'culture', 'values', 'principles', 'ethics', 'transparency', 'accountability',
        
        # Growth and scaling terms
        'scaling', 'expansion', 'market entry', 'go to market', 'gtm', 'launch',
        'product launch', 'market penetration', 'user acquisition', 'growth hacking',
        'viral', 'network effects', 'platform', 'marketplace', 'ecosystem',
        'partnership', 'collaboration', 'integration', 'automation', 'digitalization',
        
        # Financial and operational terms
        'unit economics', 'burn rate', 'runway', 'cash flow', 'profitability',
        'monetization', 'pricing', 'business model', 'value proposition', 'competitive advantage',
        'market share', 'total addressable market', 'tam', 'sam', 'som', 'analysis',
        'forecast', 'projection', 'budget', 'planning', 'resource allocation'
    ]
    
    # Group keywords by category
    categories = {
        "Core Startup Terms": startup_keywords[:25],
        "Methodologies & Frameworks": startup_keywords[25:45], 
        "Business Best Practices": startup_keywords[45:65],
        "Growth & Scaling": startup_keywords[65:80],
        "Financial & Operations": startup_keywords[80:]
    }
    
    for category, keywords in categories.items():
        print(f"\n📁 {category}:")
        for i in range(0, len(keywords), 3):
            group = keywords[i:i+3]
            print(f"   {', '.join(group)}")
    
    print(f"\n📊 TOTAL KEYWORDS SEARCHED: {len(startup_keywords)}")
    
    print("\n🤖 AI ASSESSMENT CRITERIA:")
    print("   The system uses GPT-4o-mini to analyze the first 1000 characters")
    print("   Rating scale: 1-10 where:")
    print("   • 1-3: Not business-related (personal docs, fiction, etc.)")
    print("   • 4-6: Somewhat related (mentions business but not main focus)")
    print("   • 7-10: Highly relevant (business plans, startup guides, reports)")
    
    print("\n💡 TIPS TO PASS VALIDATION:")
    print("   • Ensure your PDF contains business/startup terminology")
    print("   • Business plans, company reports, and startup guides work best")
    print("   • Avoid purely technical docs without business context")
    print("   • Academic papers should focus on business/entrepreneurship topics")

if __name__ == "__main__":
    show_validation_criteria() 