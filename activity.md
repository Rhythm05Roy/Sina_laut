# activity check

## Dynamic Prompt Builder Architecture (text diagram)
```
User Input (UI)
   -> Structured JSON (project, brand, product, slot)
      -> Master Prompt (system role)
         -> Category Template (main/infographic/lifestyle per category)
            -> Marketplace Rules (amazon/shopify/flipkart)
               -> Price Positioning Style (budget/mid/premium)
                  -> Product Analysis (GPT vision/text)
                     -> Visual Strategy (per slot)
                        -> Prompt Engineering (merge blocks)
                           -> Nano Banana Generation
                              -> Quality Review (optional)
                                 -> Response + metadata
```

## JSON Schema (simplified, scalable)
```json
{
  "project": {
    "project_name": "string",
    "brand_name": "string",
    "product_category": "string",
    "target_marketplaces": ["amazon", "shopify"]
  },
  "brand": {
    "logo_url": "string|null",
    "primary_color": "string",
    "secondary_color": "string",
    "font_heading": "string",
    "font_body": "string"
  },
  "product": {
    "sku": "string",
    "title": "string",
    "short_description": "string",
    "usps": ["string"],
    "keywords": {
      "primary": ["string"],
      "secondary": ["string"]
    },
    "languages": ["string"],
    "price_position": "budget|mid|premium"
  },
  "assets": [
    { "type": "product_photo", "url": "string" }
  ],
  "slot": {
    "slot_name": "main_product|key_facts|lifestyle|usps|comparison|cross_selling|closing",
    "image_type": "main|infographic|lifestyle",
    "style_template": "playful|modern|minimal",
    "remove_background": true
  },
  "analysis": {
    "visual_style": "string",
    "lighting": "string",
    "background": "string",
    "composition": "string",
    "must_avoid": ["string"],
    "usp_visual_strategy": { "usp": "visual idea" }
  },
  "strategy": {
    "image_type": "string",
    "text_allowed": true,
    "icons_allowed": false,
    "badge_style": "string|null",
    "max_callouts": 3,
    "background": "string",
    "composition": "string"
  },
  "prompt": "final string sent to generator",
  "qa": {
    "score": 0.0,
    "issues": ["string"],
    "suggestion": "string"
  }
}
```

## Multi-Agent Architecture (concise)
- Agent 1: Product Analyst — text/vision analysis -> `analysis` block.
- Agent 2: Visual Director — decides slot strategy -> `strategy`.
- Agent 3: Prompt Engineer — merges master prompt + category + marketplace + price + analysis + strategy -> final prompt.
- Agent 4 (optional): Quality Reviewer — scores generated image and suggests fixes -> `qa`.
