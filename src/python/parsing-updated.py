import pandas as pd
from bs4 import BeautifulSoup

# Path to the HTML file
file_path = '../../raw_data/lamunicipalcode.html'


with open(file_path, 'r', encoding='utf-8') as municipal_code:
    content = municipal_code.read()

soup = BeautifulSoup(content, 'lxml')

# Find chapters
chapters = soup.find_all('div', class_='rbox Chapter')   
chapter_data = []
for chapter in chapters:
    a_tag = chapter.find('a')
    if a_tag:
        chapter_id = a_tag.attrs['id']
    chapter_text = chapter.get_text(separator=" | ").strip()
    
    chapter_data.append({
        'Chapter ID': chapter_id,
        'Chapter Text': chapter_text
    })
    
chapter_data = pd.DataFrame.from_dict(chapter_data)

# Save chapter data to Week 6 directory
output_directory = '../../intermediate_data/'
chapter_data.to_csv(output_directory + "chapter_data.csv", header=True, index=False)

# Find articles
articles = soup.find_all('div', class_='Article toc-destination rbox')
article_data = []
for article in articles:
    a_tag = article.find('a')
    if a_tag:
        article_id = a_tag.attrs['id']
    article_text = article.get_text(separator=" | ")
    article_data.append({
        'Article ID': article_id,
        'Article Text': article_text
    })

article_data = pd.DataFrame.from_dict(article_data)

# Save article data to Week 6 directory
article_data.to_csv(output_directory + "article_data.csv", header=True, index=False)

#Find Sections

sections = soup.find_all('div', class_='Section toc-destination rbox')
section_data = []
for section in sections:
    a_tag = section.find('a')
    if a_tag:
        section_id = a_tag.attrs['id']
    section_text = section.get_text(separator=" | ")  #i saw the difference thatadding the separator makes, why is that
    section_data.append({
        'Section ID': section_id,
        'Section Text': section_text
    })
    
section_data =  pd.DataFrame.from_dict(section_data)

#Save section data to week 6 directory

section_data.to_csv(output_directory + "section_data.csv", header=True, index=False)

# Find all div elements with the class 'rbox Normal-Level'
subsections = soup.find_all('div', class_='rbox Normal-Level')

# Initialize a list to store subsection data
subsection_data = []

# Loop through each div to extract subsection content
for subsection in subsections:
    # Extract the text content of the subsection
    subsection_text = subsection.get_text(separator=" ").strip()
    
    # Append the text to the list
    if subsection_text:
        subsection_data.append({'Subsection Text': subsection_text})

# Convert to DataFrame
subsection_df = pd.DataFrame(subsection_data)

# Define output directory
output_directory = '../../intermediate_data/'

# Save subsection data to Week 6 directory
subsection_df.to_csv(output_directory + "subsection_data.csv", header=True, index=False)

# Print the DataFrame
print(subsection_df)

# Once we figure out subsections the next sub levels would be L2 and L3 


    





































