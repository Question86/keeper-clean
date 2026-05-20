import requests
import os
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# List of URLs (modified to printable version for cleaner text)
urls = [
    "https://en.wikipedia.org/w/index.php?title=Periodic_table&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=History_of_the_periodic_table&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Extended_periodic_table&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_(periodic_table)&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Period_(periodic_table)&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Block_(periodic_table)&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Types_of_periodic_tables&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Alkali_metal&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Alkaline_earth_metal&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Transition_metal&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Metalloid&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Nonmetal&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Halogen&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Noble_gas&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Lanthanide&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Actinide&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Boron_group&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Carbon_group&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Pnictogen&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Chalcogen&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Actinide_contraction&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Diagonal_relationship&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Island_of_stability&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Magic_number_(physics)&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Relative_atomic_mass&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Standard_atomic_weight&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Systematic_element_name&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Whole_number_rule&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Janet%27s_Left_Step_periodic_table&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=ADOMAH_(periodic_table)&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Periodic_table_(electron_configurations)&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Periodic_table_(crystal_structure)&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Goldschmidt_classification&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Fricke_model&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Pyykk%C3%B6_model&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Kainosymmetry&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Dividing_line_between_metals_and_nonmetals&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Element_category&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Chemical_elements_in_East_Asian_languages&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=List_of_chemical_elements_named_after_places&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=List_of_aqueous_ions_by_element&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Continent_of_stability&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Plum_pudding_model&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_1_element&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_2_element&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_3_element&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_4_element&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_5_element&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_6_element&printable=yes",
    "https://en.wikipedia.org/w/index.php?title=Group_7_element&printable=yes"
]

# Directory to save texts
output_dir = "periodic_table_texts"
os.makedirs(output_dir, exist_ok=True)

for i, url in enumerate(urls, 1):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Save the HTML content (printable version is mostly text)
            filename = f"{output_dir}/article_{i:02d}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Saved article {i}")
        else:
            print(f"Failed to fetch article {i}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching article {i}: {str(e)}")
    
    # Delay to avoid rate limiting
    if i < len(urls):
        time.sleep(15)

print("Extraction complete.")