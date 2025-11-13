import os
from dotenv import load_dotenv
from firecrawl import Firecrawl

# Call .env to get API key
load_dotenv()
firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))


# Use Firecrawl to extract data from a URL
res = firecrawl.extract(
    urls=["https://idsp.mohfw.gov.in/WriteReadData/l892s/4345056491761883941.pdf"],
    prompt="Go through each page of the PDF and extract the disease risk, date identified, location, week, and number of cases",
)

# Get job status
# job_status = firecrawl.get_extract_status(res.id)
# print(job_status)


# Print the extracted data
print(res)