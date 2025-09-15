from discord import Interaction, app_commands
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Set a timeout for the model call (e.g., 1 seconds)
MAX_MODEL_RESPONSE_TIME = 1  # seconds

base_dir = Path("./data")

def setup_movierecs(tree: app_commands.CommandTree):
    @tree.command(name="movierecs", description="Get movie recommendations from the bot.")

    async def movierecs(interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Load the personal ratings dataset
        personal_ratings_df = pd.read_csv(base_dir / 'personal_ratings.csv')
        
        interaction_user_id = interaction.user.id
        
        user_movies = personal_ratings_df[personal_ratings_df['userId'] == interaction_user_id]['movieId'].unique()

        # If the user hasn't rated any movies, inform them
        if len(user_movies) == 0:
            await interaction.followup.send("You haven't rated any movies yet. Please rate some movies to get recommendations!")
            return
        
        # Load the movies and the ratings dataset
        ratings_df = pd.read_csv(base_dir / 'ratings.csv')
        movies_df = pd.read_csv(base_dir / 'movies.csv')
        
        movies_df = movies_df[['title', 'genres']]
        
        user_item_matrix = ratings_df.pivot(index=['userId'], columns=['movieId'], values='rating').fillna(0)

        # Split the genres string into a list of genres
        movies_df['genres'] = movies_df['genres'].str.split('|')

        # Extract unique genres from the user's rated movies
        user_genres = movies_df[movies_df['movieId'].isin(user_movies)]['genres'].explode().unique()

        # Filter movies by the user's genres
        filtered_movies = movies_df[movies_df['genres'].apply(lambda x: any(genre in x for genre in user_genres))]

        # Merge with average ratings
        filtered_movies = filtered_movies.merge(average_ratings, on='movieId')

        # Sort by average rating in descending order
        filtered_movies = filtered_movies.sort_values('avg_rating', ascending=False)

        response = "Top Movie Recommendations:\n\n"
        
        for _, row in filtered_movies.head(10).iterrows():
            response += f"{row['title']} - Genres: {', '.join(row['genres'])}\n\n"

        await interaction.followup.send(response, ephemeral=True)