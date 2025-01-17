import os
import requests
import re

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",  # Notion APIのバージョンを最新に更新してください
    "Content-Type": "application/json",
}


def get_database_items():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    filter_body = {}
    response = requests.post(url, headers=headers, json=filter_body)
    response.raise_for_status()
    return response.json()["results"]


def get_item_properties(item):
    item_properties = {}
    for key, value in item["properties"].items():
        if value["type"] == "title":
            item_properties[key] = value["title"][0]["text"]["content"] if value["title"] else ""
        elif value["type"] == "rich_text":
            item_properties[key] = value["rich_text"][0]["text"]["content"] if value["rich_text"] else ""
        elif value["type"] == "number":
            item_properties[key] = value["number"]
        elif value["type"] == "select":
            item_properties[key] = value["select"]["name"] if value["select"] else ""
        elif value["type"] == "multi_select":
            item_properties[key] = [option["name"]
                                    for option in value["multi_select"]] if value["multi_select"] else []
        elif value["type"] == "date":
            item_properties[key] = value["date"]["start"] if value["date"] else ""
        elif value["type"] == "files":
            item_properties[key] = [file["name"]
                                    for file in value["files"]] if value["files"] else []
        elif value["type"] == "checkbox":
            item_properties[key] = value["checkbox"]
        elif value["type"] == "url":
            item_properties[key] = value["url"] if value["url"] else ""
        elif value["type"] == "email":
            item_properties[key] = value["email"] if value["email"] else ""
        elif value["type"] == "phone_number":
            item_properties[key] = value["phone_number"] if value["phone_number"] else ""
        elif value["type"] == "formula":
            item_properties[key] = value["formula"]["string"] if "string" in value["formula"] else value["formula"]["number"]
        elif value["type"] == "relation":
            item_properties[key] = [related_item["id"]
                                    for related_item in value["relation"]] if value["relation"] else []
        elif value["type"] == "rollup":
            item_properties[key] = value["rollup"]["value"] if value["rollup"] else ""
        # ... 他のプロパティタイプも必要に応じて追加
        else:
            item_properties[key] = ""

    return item_properties


def is_item_valid(item_properties):
    required_keys = ["No.", "パターン名", "状態"]
    for key in required_keys:
        if key not in item_properties:
            return False
    return True

def create_id_to_pattern_name_map(items):
    id_to_pattern_name = {}
    for item in items:
        item_properties = get_item_properties(item)
        id_to_pattern_name[item["id"]] = '* <<_' + item_properties["パターン名"] + '>>'
    return id_to_pattern_name


def create_asciidoc_file(item_properties, id_to_pattern_name):
    file_name = f"contents/patterns/{item_properties['No.']}.adoc"
    
    with open(file_name, 'w', encoding='utf-8') as file:
        
        # レベル1のヘッダーを作成
        file.write(f"= {item_properties['パターン名']}\n\n")


        # Asciidocのセクションと定義リストを書く
        section_mapping = {
            "はじめに": "はじめに(サブタイトル的に内容を推測できるもの)",
            "要約": "要約(使用例を除く詳細をまとめ理解を促すもの)",
            "状況": "状況",
            "問題": "問題",
            "フォース": "フォース(問題に至る背景)",
            "解決方法": "解決方法",
            "結果状況": "結果状況(パターンの適用が上手くいった状況)",
            "使用例": "使用例(カードを切るタイミングや背景)",
            "関連パターン": "関連パターン"
        }
        
        for section_title, property_name in section_mapping.items():
            # 項目名と値を取得
            content = item_properties.get(property_name, "")
            
            # 項目の値がリストであり、かつ空でない場合のみ出力
            if isinstance(content, list) and content:
                # '関連パターン' セクションの処理
                if property_name == "関連パターン":
                    # IDからパターン名を取得し、リストをカンマ区切りの文字列に変換
                    content = [id_to_pattern_name.get(related_id, "Unknown pattern") for related_id in content]
                    content = '\n'.join(content) if content else None
                else:
                    # その他のリスト型プロパティの処理
                    content = ', '.join(content)
            # 項目の値が文字列または数値で、空でない場合のみ出力
            elif isinstance(content, (int, float))  and content:
                content = str(content)
            elif content:
                texts = content.splitlines()
                content = ""
                for linetext in texts:
                    print(f"linetext: {linetext}")
                    t = re.subn("^・", "* ", linetext)
                    linetext = t[0]
                    sub_count = t[1]
                    t = re.subn("^　・", "** ", linetext)
                    linetext = t[0]
                    sub_count += t[1]
                    if content == "":
                        content = linetext
                    elif sub_count != 0:
                        content += "\n" + linetext
                    elif linetext.endswith('::'):
                        content += "\n" + linetext
                    elif content.endswith('::'):
                        content += "\n" + linetext
                    else:
                        content += " +" + "\n" + linetext
            
            # 項目の内容を書き込み
            if content:  # コンテンツが有効な値の場合のみ書き込み
                file.write(f"{section_title}::\n")
                file.write(f"{content}\n\n")
                
        file.write(f"\n\n")

if __name__ == "__main__":
    items = get_database_items()
    id_to_pattern_name_map = create_id_to_pattern_name_map(items)
    for item in items:
        item_properties = get_item_properties(item)
        if is_item_valid(item_properties) and (item_properties['状態'] == "公開前" or item_properties['状態'] == "使用例以外二次校済"):
            print(f"output item: {item_properties}")
            create_asciidoc_file(item_properties, id_to_pattern_name_map)
        else:
            print(f"Invalid item: {item_properties}")
