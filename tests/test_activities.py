"""Test suite for Mergington High School Activities API"""

import pytest


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that get_activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Basketball Club" in data
        assert "Tennis Club" in data
        assert "Art Club" in data
        assert len(data) > 0

    def test_get_activities_has_required_fields(self, client, reset_activities):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_has_correct_participant_data(self, client, reset_activities):
        """Test that activities have correct initial participant data"""
        response = client.get("/activities")
        data = response.json()
        
        assert "james@mergington.edu" in data["Basketball Club"]["participants"]
        assert "grace@mergington.edu" in data["Tennis Club"]["participants"]
        assert len(data["Art Club"]["participants"]) == 2


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball%20Club/signup?email=newemail@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newemail@mergington.edu" in data["message"]
        assert "Basketball Club" in data["message"]

    def test_signup_adds_participant_to_activity(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        client.post(
            "/activities/Basketball%20Club/signup?email=test@mergington.edu"
        )
        
        response = client.get("/activities")
        data = response.json()
        
        assert "test@mergington.edu" in data["Basketball Club"]["participants"]

    def test_signup_for_nonexistent_activity(self, client, reset_activities):
        """Test signup for activity that doesn't exist"""
        response = client.post(
            "/activities/Fake%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_duplicate_email(self, client, reset_activities):
        """Test signup with email already registered for activity"""
        response = client.post(
            "/activities/Basketball%20Club/signup?email=james@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_different_activity_same_email(self, client, reset_activities):
        """Test that same email can sign up for different activities"""
        # Sign up for Basketball Club (should fail - already signed up)
        response1 = client.post(
            "/activities/Basketball%20Club/signup?email=james@mergington.edu"
        )
        assert response1.status_code == 400
        
        # Sign up for Tennis Club (should succeed - different activity)
        response2 = client.post(
            "/activities/Tennis%20Club/signup?email=james@mergington.edu"
        )
        assert response2.status_code == 200

    def test_signup_multiple_participants(self, client, reset_activities):
        """Test that multiple participants can sign up for same activity"""
        client.post(
            "/activities/Basketball%20Club/signup?email=email1@mergington.edu"
        )
        client.post(
            "/activities/Basketball%20Club/signup?email=email2@mergington.edu"
        )
        
        response = client.get("/activities")
        data = response.json()
        
        participants = data["Basketball Club"]["participants"]
        assert "email1@mergington.edu" in participants
        assert "email2@mergington.edu" in participants
        assert len(participants) >= 3  # original + 2 new


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_participant_success(self, client, reset_activities):
        """Test successful removal of a participant"""
        response = client.delete(
            "/activities/Basketball%20Club/participants/james@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Removed" in data["message"]

    def test_remove_participant_removes_from_list(self, client, reset_activities):
        """Test that removal actually removes the participant"""
        client.delete(
            "/activities/Basketball%20Club/participants/james@mergington.edu"
        )
        
        response = client.get("/activities")
        data = response.json()
        
        assert "james@mergington.edu" not in data["Basketball Club"]["participants"]

    def test_remove_participant_from_nonexistent_activity(self, client, reset_activities):
        """Test removal from activity that doesn't exist"""
        response = client.delete(
            "/activities/Fake%20Activity/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_remove_nonexistent_participant(self, client, reset_activities):
        """Test removal of participant not in the activity"""
        response = client.delete(
            "/activities/Basketball%20Club/participants/notinlist@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "not found" in data["detail"]

    def test_remove_multiple_participants(self, client, reset_activities):
        """Test removing multiple participants"""
        original_count = len(
            client.get("/activities").json()["Art Club"]["participants"]
        )
        
        client.delete(
            "/activities/Art%20Club/participants/isabella@mergington.edu"
        )
        client.delete(
            "/activities/Art%20Club/participants/lucas@mergington.edu"
        )
        
        response = client.get("/activities")
        data = response.json()
        
        new_count = len(data["Art Club"]["participants"])
        assert new_count == original_count - 2

    def test_remove_and_re_enroll_same_participant(self, client, reset_activities):
        """Test that a removed participant can re-enroll"""
        # Remove
        client.delete(
            "/activities/Basketball%20Club/participants/james@mergington.edu"
        )
        
        # Verify removal
        response = client.get("/activities")
        assert "james@mergington.edu" not in response.json()["Basketball Club"]["participants"]
        
        # Re-enroll
        response = client.post(
            "/activities/Basketball%20Club/signup?email=james@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify re-enrollment
        response = client.get("/activities")
        assert "james@mergington.edu" in response.json()["Basketball Club"]["participants"]


class TestIntegrationScenarios:
    """Integration tests for complete user workflows"""

    def test_signup_and_remove_workflow(self, client, reset_activities):
        """Test complete workflow: signup, verify, remove, verify"""
        email = "workflow@mergington.edu"
        activity = "Chess%20Club"
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
        
        # Remove
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        assert email not in response.json()["Chess Club"]["participants"]

    def test_activities_data_consistency(self, client, reset_activities):
        """Test that participant counts stay consistent"""
        activity_data_before = client.get("/activities").json()
        initial_count = len(activity_data_before["Basketball Club"]["participants"])
        
        # Add participant
        client.post(
            "/activities/Basketball%20Club/signup?email=new@mergington.edu"
        )
        
        activity_data_after_add = client.get("/activities").json()
        after_add_count = len(activity_data_after_add["Basketball Club"]["participants"])
        assert after_add_count == initial_count + 1
        
        # Remove participant
        client.delete(
            "/activities/Basketball%20Club/participants/new@mergington.edu"
        )
        
        activity_data_after_remove = client.get("/activities").json()
        after_remove_count = len(activity_data_after_remove["Basketball Club"]["participants"])
        assert after_remove_count == initial_count
