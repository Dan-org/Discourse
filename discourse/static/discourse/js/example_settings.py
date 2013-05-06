hide comments
upvote comments
restrict depth
sort comments per depth
length counter
size hider


// Todo: length counter | ajax indicator | hide comments | reply | edit | report


DISCOURSE_THREAD_SETTINGS = {
    'max_length': 500,            # Allow only 500 characters max.
    'hide_length': 200,           # Hide comment bodies after the first 200 characters.
    'submit_on_enter': True,      # The enter key submits the comment form.
    'hide_after': None,           # Don't hide any comments after a certain amount
    'hide_before': None,          # Don't hide any comments before a certain amount
    'hide_lower_than': 0,         # Hide comments with a score of 0 or less.  (Comments start at 1)
    'upvotes': True,              # Allow upvotes / likes
    'downvotes': False,           # Allow downvotes
    'max_depth': 2,               # Allow a depth of 2, meaning only one reply level, max_depth = 1 is no replies.
    'allow_edit': True,           # Allow comments to be edited by the author
    'allow_delete': True,         # Allow comments to be deleted by the author
    'allow_report': True,         # Allow comments to be reported
    'hide_reported': 7,           # Hide comments that have been reported 7 or more times.
    'sort': ('-score', 'created') # Sort by score then created
    'depth-2': {                  # Only for depth 2:
        'sort': ('created')           # Sort by created
        'hide_before': 3,             # Hide all the comments before the first 3
    }
}