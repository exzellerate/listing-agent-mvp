import { useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import {
  ChevronDown,
  ChevronRight,
  ShoppingBag,
  Camera,
  HelpCircle,
  MessageSquare,
  Rocket,
  Settings,
  DollarSign,
  AlertTriangle,
  FileText,
} from 'lucide-react';

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQCategory {
  title: string;
  icon: React.ElementType;
  id: string;
  items: FAQItem[];
}

const faqCategories: FAQCategory[] = [
  {
    title: 'Getting Started',
    icon: Rocket,
    id: 'getting-started',
    items: [
      {
        question: 'How do I upload product images?',
        answer:
          'Navigate to "Upload & Analyze" from the sidebar. You can drag and drop up to 5 images or click to browse your files. Supported formats include JPEG, PNG, and WebP. Each image should be under 20MB.',
      },
      {
        question: 'What image formats and sizes are supported?',
        answer:
          'We support JPEG, PNG, and WebP formats. Images should be at least 500x500 pixels for best results. Maximum file size is 20MB per image. For eBay listings, images must be at least 500px on the longest side.',
      },
      {
        question: 'How does the AI analysis work?',
        answer:
          'Our AI examines each uploaded image independently, then cross-references findings across all images. It identifies the product, extracts details like brand, model, condition, and features, then generates optimized titles, descriptions, and pricing suggestions.',
      },
      {
        question: 'Can I select different marketplace platforms?',
        answer:
          'Yes! During upload you can choose between eBay, Amazon, and Walmart. Each platform has different listing requirements, and the AI tailors its output accordingly. eBay is currently the most fully supported platform with direct publishing.',
      },
    ],
  },
  {
    title: 'eBay Setup',
    icon: ShoppingBag,
    id: 'ebay-setup',
    items: [
      {
        question: 'How do I connect my eBay account?',
        answer:
          'Go to Settings > Connections and click "Connect eBay Account." You\'ll be redirected to eBay to authorize the app. Once approved, you\'ll be sent back automatically. Your connection stays active until you revoke it.',
      },
      {
        question: 'What are business policies and do I need them?',
        answer:
          'eBay business policies define your payment, shipping, and return rules. They\'re required for listing via the API. Set them up in your eBay Seller Hub under "Business Policies" before trying to publish. You need at least one payment, one shipping, and one return policy.',
      },
      {
        question: 'How does token refresh work?',
        answer:
          'eBay access tokens expire after 2 hours, but the app automatically refreshes them using your refresh token (valid for 18 months). If your connection stops working, try disconnecting and reconnecting in Settings.',
      },
      {
        question: 'Is the app using eBay sandbox or production?',
        answer:
          'The app uses the eBay production environment by default. Listings you publish are real and visible on eBay. There is no sandbox/test mode — everything is live.',
      },
    ],
  },
  {
    title: 'Listing Creation',
    icon: FileText,
    id: 'listing-creation',
    items: [
      {
        question: 'Can I edit the AI-generated title and description?',
        answer:
          'Absolutely! After analysis, all fields are fully editable. Click on any field in the results form to modify it. The AI-generated content is a starting point — feel free to adjust titles, descriptions, specifics, and pricing to your liking.',
      },
      {
        question: 'How do categories and item specifics work?',
        answer:
          'The AI suggests an eBay category based on the product. You can search and change it. Once a category is selected, eBay-required and recommended item specifics (like Brand, Size, Color) appear. Fill in as many as possible — more specifics mean better search visibility.',
      },
      {
        question: 'How is condition determined?',
        answer:
          'The AI analyzes visible wear, damage, or packaging in your images to suggest a condition (New, Like New, Very Good, Good, Acceptable). You can override this. Be accurate — eBay has specific condition definitions and buyers expect honesty.',
      },
      {
        question: 'Can I save a listing as a draft?',
        answer:
          'Yes. After analysis, click "Save as Draft" instead of publishing. Drafts are saved with all your edits and images. Access them from the "Drafts" page in the sidebar. You can resume editing and publish whenever you\'re ready.',
      },
    ],
  },
  {
    title: 'Image Best Practices',
    icon: Camera,
    id: 'image-best-practices',
    items: [
      {
        question: 'What makes a good product photo?',
        answer:
          'Use natural or bright, even lighting. Shoot against a clean, uncluttered background (white or neutral works best). Ensure the product fills most of the frame and is in sharp focus. Multiple angles help the AI extract more details.',
      },
      {
        question: 'How many images should I upload?',
        answer:
          'Upload 2-5 images for best results. Include: a front/main view, back view, any labels or branding, close-ups of notable features or flaws, and the item in its packaging if applicable. More angles give the AI (and buyers) a complete picture.',
      },
      {
        question: 'What should I avoid in product photos?',
        answer:
          'Avoid dark or uneven lighting, cluttered backgrounds, blurry images, heavy filters, and watermarks. Don\'t include personal items or sensitive information in the frame. Avoid extreme angles that misrepresent the product size.',
      },
      {
        question: 'Does image resolution matter?',
        answer:
          'Yes. Higher resolution images allow the AI to read text, identify brands, and spot details. Aim for at least 1000x1000 pixels. eBay requires a minimum of 500px on the longest side, but recommends 1600px for zoom functionality.',
      },
    ],
  },
  {
    title: 'Pricing',
    icon: DollarSign,
    id: 'pricing',
    items: [
      {
        question: 'How does AI pricing work?',
        answer:
          'The AI researches current market prices by searching for similar items on eBay and other sources. It considers the product\'s condition, brand, model, and current market trends to suggest a competitive price range.',
      },
      {
        question: 'Can I edit the suggested price?',
        answer:
          'Yes, the suggested price is just a recommendation. You can set any price you want in the listing form. The AI provides a price range (low, suggested, high) to help you decide.',
      },
      {
        question: 'How accurate is the market comparison?',
        answer:
          'The AI uses web search to find recent sold and active listings for similar products. Accuracy depends on how unique the item is — common products get very accurate pricing, while rare or niche items may need manual adjustment.',
      },
    ],
  },
  {
    title: 'Troubleshooting',
    icon: AlertTriangle,
    id: 'troubleshooting',
    items: [
      {
        question: 'The analysis is taking too long or timing out.',
        answer:
          'Analysis typically takes 30-60 seconds. If it times out (over 3 minutes), try: uploading fewer images, using smaller file sizes, or checking your internet connection. Web search-enhanced analysis takes longer but provides better pricing data.',
      },
      {
        question: 'My eBay listing failed to publish.',
        answer:
          'Common causes: missing business policies (set up in eBay Seller Hub), expired eBay connection (reconnect in Settings), missing required item specifics, or images that don\'t meet eBay\'s requirements. Check the error message for specifics.',
      },
      {
        question: 'I\'m seeing "invalid JSON" or parsing errors.',
        answer:
          'This usually happens when the AI response is interrupted or malformed. Try re-running the analysis. If it persists, try with fewer images or different images. This is rare but can occur with very complex or unusual products.',
      },
      {
        question: 'My eBay sync isn\'t showing all listings.',
        answer:
          'The sync imports active listings from eBay. It may take a moment to complete. If listings are missing, try clicking the sync button again. Only active (not ended or sold) listings are imported.',
      },
      {
        question: 'Images aren\'t uploading to eBay.',
        answer:
          'eBay requires images to be at least 500px on the longest side, in JPEG/PNG format, and under 12MB. The app converts images to WebP for storage but uploads them in eBay-compatible formats. If uploads fail, check your eBay connection status.',
      },
    ],
  },
];

const quickLinks = [
  {
    title: 'Getting Started',
    description: 'Learn how to upload images and create your first listing',
    icon: Rocket,
    targetId: 'getting-started',
  },
  {
    title: 'eBay Setup',
    description: 'Connect your eBay account and configure business policies',
    icon: Settings,
    targetId: 'ebay-setup',
  },
  {
    title: 'Best Practices',
    description: 'Tips for better photos and higher-quality listings',
    icon: Camera,
    targetId: 'image-best-practices',
  },
];

export default function HelpPage() {
  const [openItems, setOpenItems] = useState<Set<string>>(new Set());

  const toggleItem = (key: string) => {
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <HelpCircle className="w-8 h-8 text-gray-900" />
            <h1 className="text-3xl font-bold text-gray-900">Help & FAQ</h1>
          </div>
          <p className="text-gray-500 text-lg">
            Everything you need to know about creating marketplace listings with AI.
          </p>
        </div>

        {/* Quick-link cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
          {quickLinks.map((link) => {
            const Icon = link.icon;
            return (
              <button
                key={link.targetId}
                onClick={() => scrollToSection(link.targetId)}
                className="text-left p-5 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all"
              >
                <Icon className="w-6 h-6 text-gray-900 mb-3" />
                <h3 className="font-semibold text-gray-900 mb-1">{link.title}</h3>
                <p className="text-sm text-gray-500">{link.description}</p>
              </button>
            );
          })}
        </div>

        {/* FAQ Accordion */}
        <div className="space-y-8">
          {faqCategories.map((category) => {
            const CategoryIcon = category.icon;
            return (
              <div key={category.id} id={category.id} className="scroll-mt-6">
                <div className="flex items-center gap-2 mb-4">
                  <CategoryIcon className="w-5 h-5 text-gray-700" />
                  <h2 className="text-xl font-semibold text-gray-900">{category.title}</h2>
                </div>
                <div className="border border-gray-200 rounded-xl overflow-hidden divide-y divide-gray-200">
                  {category.items.map((item, idx) => {
                    const key = `${category.id}-${idx}`;
                    const isOpen = openItems.has(key);
                    return (
                      <div key={key} className="bg-white">
                        <button
                          onClick={() => toggleItem(key)}
                          className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
                        >
                          <span className="font-medium text-gray-900 pr-4">{item.question}</span>
                          {isOpen ? (
                            <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
                          ) : (
                            <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                          )}
                        </button>
                        {isOpen && (
                          <div className="px-5 pb-4">
                            <p className="text-gray-600 leading-relaxed">{item.answer}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Still need help? */}
        <div className="mt-12 bg-gray-50 border border-gray-200 rounded-xl p-8 text-center">
          <MessageSquare className="w-8 h-8 text-gray-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Still need help?</h3>
          <p className="text-gray-500 mb-4">
            Can't find what you're looking for? Send us your question or feedback.
          </p>
          <Link
            to="/feedback"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium"
          >
            <MessageSquare className="w-4 h-4" />
            Send Feedback
          </Link>
        </div>
      </div>
    </Layout>
  );
}
