from starlette.requests import Request
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse, Response

from configs import COOKIE, ORIGIN, REFERER, X_REQ_ID, X_CSRF_TOKEN

HEADERS = {
    "cookie": COOKIE,
    "origin": ORIGIN,
    "referer": REFERER,
    "x-request-id": X_REQ_ID,
    "x-csrf-token": X_CSRF_TOKEN,
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "apollographql-client-name": "consumer",
    "apollographql-client-version": "1.2",
    "content-type": "application/json",
    "graphql-operation-type": "query",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
}

QUERY = """
query JobSearchQuery($first: Int, $after: String, $input: JobSearchInput) {
  jobSearch(first: $first, after: $after, input: $input) {
    totalCount
    searchId
    ...JobSearchResultsList_JobSearchResultConnection
    edges {
      node {
        id
        shouldPromote
        isPromoted
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment JobDetails_Header_Job on Job {
  id
  title
  createdAt
  expirationDate
  employer {
    id
    name
    logo { url(size: "small") __typename }
    industry { id name __typename }
    __typename
  }
  __typename
}

fragment JobDetails_Benefits_Job on Job {
  id
  title
  remunerations { id behaviorIdentifier __typename }
  employer { id __typename }
  additionalBenefitsLink
  salaryRange {
    id min max currency
    paySchedule { id behaviorIdentifier name friendlyName __typename }
    __typename
  }
  salaryType { id name behaviorIdentifier __typename }
  payCurrencyCode
  __typename
}

fragment JobDetails_Description_Job on Job {
  id
  description
  employer { id __typename }
  __typename
}

fragment JobDetails_AtAGlance_Job on Job {
  id
  startDate
  endDate
  workSchedule { id hours interval __typename }
  __typename
}

fragment JobDetails_Documents_Attachment on Job {
  id
  attachments {
    id
    name
    simpleType
    document { contentType originalFilename __typename }
    __typename
  }
  __typename
}

fragment JobDetails_SimilarJobs_Job on Job {
  id
  employer { id __typename }
  __typename
}

fragment JobDetails_JobCollections_Job on Job {
  id
  employer { id __typename }
  __typename
}

fragment JobDetails_Basic_Job on Job {
  id
  ...JobDetails_Header_Job
  ...JobDetails_Benefits_Job
  ...JobDetails_Description_Job
  ...JobDetails_AtAGlance_Job
  ...JobDetails_Documents_Attachment
  ...JobDetails_SimilarJobs_Job
  ...JobDetails_JobCollections_Job
  __typename
}

fragment JobSearchResultCard_JobSearchResult on JobSearchResult {
  id
  isPromoted
  shouldPromote
  job {
    id
    title
    ...JobDetails_Basic_Job
    __typename
  }
  __typename
}

fragment JobSearchPagination_JobSearchResultConnection on JobSearchResultConnection {
  totalCount
  __typename
}

fragment JobSearchResultsList_JobSearchResultConnection on JobSearchResultConnection {
  totalCount
  searchId
  edges {
    node {
      id
      ...JobSearchResultCard_JobSearchResult
      job {
        id
        ...JobDetails_Basic_Job
        __typename
      }
      __typename
    }
    __typename
  }
  ...JobSearchPagination_JobSearchResultConnection
  __typename
}
"""


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    a simple JSON response that includes the details of the rate limit
    that was hit. If no limit is hit, the countdown is added to headers.
    """
    response = JSONResponse(
        {"message": 'Too many requests (Rate limit reached). Please try again in sometime.'}, status_code=200
    )
    response = request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
    return response