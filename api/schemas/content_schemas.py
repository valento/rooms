READ_DATA_SCHEMA = {
    "type": "object",
    "required": ["title", "body"],
    "properties": {
        "title": {"type": "string", "maxLength": 255},
        "body": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "content_type": {"type": "string", "const": "read"},
                "read_category": {"type": "string", "enum": ["blog", "about", "doc", "event"]},
                "subcategory": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "priority": {"type": "integer", "minimum": 0, "maximum": 10},
                "status": {"type": "string", "enum": ["draft", "published", "archived"]},
                "author": {"type": "string"},
                "client": {"type": "string"},
                "industry": {"type": "string"},
                "pricing": {"type": "string"},
                "app_id": {"type": "integer"},
                "parent_id": {"type": "integer"},
                "seo_keywords": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
}

READ_UI_SCHEMA = {
    "elements": [
        {"field": "title", "widget": "input", "placeholder": "Title"},
        {"field": "metadata.read_category", "widget": "select"},
        {"field": "metadata.subcategory", "widget": "input", "placeholder": "Subcategory"},
        {"field": "metadata.tags", "widget": "tag-input", "placeholder": "Add tags"},
        {"field": "body", "widget": "textarea", "rows": 15, "placeholder": "Content (Markdown)..."},
        {"field": "metadata.author", "widget": "input", "placeholder": "Author (optional)"},
        {"field": "metadata.priority", "widget": "slider", "min": 0, "max": 10},
        {"field": "metadata.status", "widget": "select"},
        {"field": "metadata.seo_keywords", "widget": "tag-input", "placeholder": "SEO keywords"}
    ]
}

def get_schemas(content_type: str):
    """Get data and UI schemas based on content_type."""
    if content_type == "read":
        return (READ_DATA_SCHEMA, READ_UI_SCHEMA)