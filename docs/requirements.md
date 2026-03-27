# Home Building Regulatory Engine

Languages: Python (backend), TypeScript (frontend)
Cloud: AWS
Tools: PostGres, PostGIS, Shapely
Optional but recommended: Any AI/ML framework
THIS IS JUST A DEMO 

---

## Requirements

Goal: Determine what can be confidently built on a parcel.

- Allow users to search for specific parcles by address / APN
- Provide a evidence-backed buildability assessment that:
  - Identifies zoning codes & regulation that relate to the parcel
  - Shows supporting resources/docs/data
  - Defines what is allowed & confidence in that conclusion
- Show map of parcels and buildings 
- Show reasonable interpretations when regulations are ambiguous / incomplete (edge cases, bad data)

Likely requires...
- Use public parcel, zoning, and regulatory info 
- Transforming data into standard format w/ parcel-specific constraints
- Have an LLM provide confidence signals & explain derivation (due to fuzzyness, edge cases, bad data, etc)

Ideally:
- Make it easy to understand relevant regulatory questions. Prioritize user experience & ismple information portrayal
- Test range of residential parcels/addresses & building types (Single Family, ADU, Guest House, etc)
- Architecture is designed to scale: LA City -> Nationwide. 

Misc:
- Scope is limited to residential parcels in LA


Bonus Features:

- Output can use description inputs (e.g. 1BR, 1B) to find parcels
- Allow users to provide feedback on responses
- Have a chat interface that can better explain the underlying dataset
- Have the map be interactive with data annotations
- Include an admin interface that shows the regulatory engine pipeline
  - Bonus+: Able to adjust system settings